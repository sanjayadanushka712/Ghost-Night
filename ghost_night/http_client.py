"""Raw HTTP mode — no browser.

Sends requests that carry a coherent identity at the *network* layer rather
than the JS layer: the TLS ClientHello (JA3/JA4), HTTP/2 settings, header order,
and User-Agent all describe ONE real browser on ONE machine.

TLS-first: curl_cffi impersonation profiles decide the TLS + HTTP/2 fingerprint.
We then derive a device profile (OS/screen/tz/locale) and a User-Agent that are
consistent with the chosen browser, so the UA never disagrees with the JA3.

Honest scope: this only shapes what the server sees at L7/TLS. It announces no
JS navigator surface at all (there is no JS engine), which is itself a signal on
sites that require scripts — use the browser path for those.
"""

import json
import random
import time

# device profiles (import kept lazy-friendly so this module stands alone)
from .session import PROFILES, FF_OS, UA_OS, TZ_COUNTRY

try:
    from curl_cffi import requests as cffi_requests
    _HAVE_CFFI = True
except Exception:  # pragma: no cover - environment without curl_cffi
    cffi_requests = None
    _HAVE_CFFI = False

# TLS-first: (impersonate token, engine, chrome major implied by the token)
# curl_cffi ships modern tokens; we pick the newest per family and a few
# historical ones so the fleet looks like a real population of versions.
CHROME_IMPERSONATE = [
    'chrome146', 'chrome145', 'chrome142', 'chrome136', 'chrome133a',
    'chrome131', 'chrome124', 'chrome123', 'chrome120',
]
FIREFOX_IMPERSONATE = ['firefox147', 'firefox144', 'firefox135', 'firefox133']
SAFARI_IMPERSONATE = ['safari260', 'safari184', 'safari180', 'safari172_ios']


def available_impersonate():
    """Return which impersonate tokens this curl_cffi build actually has."""
    if not _HAVE_CFFI:
        return set()
    try:
        from curl_cffi.requests import BrowserType
        return {b.name for b in BrowserType}
    except Exception:
        return set()


def _chrome_token_major(token):
    # 'chrome146' / 'chrome131_android' / 'chrome133a'
    digits = ''.join(c for c in token[len('chrome'):] if c.isdigit())
    return int(digits) if digits else 0


def _firefox_token_major(token):
    digits = ''.join(c for c in token[len('firefox'):] if c.isdigit())
    return int(digits) if digits else 0


def _pick_token(engine):
    have = available_impersonate()
    if engine == 'firefox':
        pool = [t for t in FIREFOX_IMPERSONATE if t in have] or FIREFOX_IMPERSONATE
    elif engine == 'safari':
        pool = [t for t in SAFARI_IMPERSONATE if t in have] or SAFARI_IMPERSONATE
    else:
        pool = [t for t in CHROME_IMPERSONATE if t in have] or CHROME_IMPERSONATE
    # bias toward the newest couple but keep some spread
    return random.choice(pool[:3]) if random.random() < 0.6 else random.choice(pool)


def build_identity(engine='chrome', geo_country=None):
    """Pick a coherent identity: TLS token -> OS-appropriate device profile ->
    matching User-Agent. Returns a dict describing the whole story."""
    token = _pick_token(engine)
    # curl_cffi only impersonates win/mac for chrome and win/mac/linux for ff;
    # keep the OS families the token plausibly represents.
    if engine == 'firefox':
        os_choices = ['win', 'mac', 'linux']
    elif engine == 'safari':
        os_choices = ['mac']
    else:
        os_choices = ['win', 'mac', 'linux']

    pool = [p for p in PROFILES if p['os'] in os_choices]
    if geo_country:
        geo_country = geo_country.upper()
        matching = [p for p in pool if TZ_COUNTRY.get(p['tz']) == geo_country]
        if matching:
            pool = matching
    profile = random.choice(pool)

    if engine == 'firefox':
        major = _firefox_token_major(token) or 140
        rv = str(major)
        ua = ('Mozilla/5.0 (' + FF_OS[profile['os']][0] + rv
              + ') Gecko/20100101 Firefox/' + rv)
        platform = FF_OS[profile['os']][1]
        vendor = ''
    elif engine == 'safari':
        ver = token[len('safari'):].replace('260', '26.0').replace('184', '18.4')
        if '_ios' in token:
            ua = ('Mozilla/5.0 (iPhone; CPU iPhone OS 18_4 like Mac OS X) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 '
                  'Mobile/15E148 Safari/604.1')
        else:
            ua = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/' + ver
                  + ' Safari/605.1.15')
        platform = 'MacIntel'
        vendor = 'Apple Computer, Inc.'
    else:
        major = _chrome_token_major(token) or 140
        ua = ('Mozilla/5.0 (' + UA_OS[profile['os']][0]
              + ') AppleWebKit/537.36 (KHTML, like Gecko) Chrome/'
              + str(major) + '.0.0.0 Safari/537.36')
        platform = UA_OS[profile['os']][1]
        vendor = 'Google Inc.'

    return {
        'impersonate': token,
        'engine': engine,
        'ua': ua,
        'platform': platform,
        'vendor': vendor,
        'locale': profile['locale'],
        'tz': profile['tz'],
        'os': profile['os'],
        'screen': profile['screen'],
        'cores': profile['cores'],
        'memory': profile['memory'],
    }


def _accept_language(locale):
    return locale + ',' + locale.split('-')[0] + ';q=0.9'


def _header_order(engine, ident):
    """Return an ordered dict of headers as a real browser would send them."""
    lang = _accept_language(ident['locale'])
    if engine == 'firefox':
        h = {
            'User-Agent': ident['ua'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': lang,
            'Accept-Encoding': 'gzip, deflate, br',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Connection': 'keep-alive',
        }
    elif engine == 'safari':
        h = {
            'User-Agent': ident['ua'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': lang,
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    else:
        h = {
            'sec-ch-ua': ('"Google Chrome";v="%s", "Chromium";v="%s", "Not_A Brand";v="24"'
                          % (_ua_major(ident['ua']), _ua_major(ident['ua']))),
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"%s"' % {
                'win': 'Windows', 'mac': 'macOS', 'linux': 'Linux'}.get(ident['os'], 'Windows'),
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': ident['ua'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': lang,
        }
    return h


def _ua_major(ua):
    import re
    m = re.search(r'(?:Chrome|Chromium)/(\d+)', ua)
    return m.group(1) if m else '140'


class RawClient:
    """A coherent, cookie-persistent raw HTTP client bound to one identity and
    one route (tor / proxy / direct)."""

    def __init__(self, engine='chrome', proxy=None, geo_country=None,
                 identity=None, timeout=30):
        if not _HAVE_CFFI:
            raise RuntimeError(
                'curl_cffi not installed — run: '
                'pip install curl_cffi (in the ghost_night venv)')
        self.ident = identity or build_identity(engine=engine, geo_country=geo_country)
        self.engine = self.ident['engine']
        self.proxy = proxy
        self.timeout = timeout
        self.session = cffi_requests.Session(
            impersonate=self.ident['impersonate'],
            headers=self.base_headers(),
        )
        if proxy:
            self.session.proxies = {'http': proxy, 'https': proxy}

    def base_headers(self):
        return _header_order(self.engine, self.ident)

    def request(self, method, url, **kw):
        headers = kw.pop('headers', None)
        r = self.session.request(
            method, url, headers=headers, timeout=self.timeout,
            allow_redirects=kw.pop('allow_redirects', True), **kw)
        return r

    def get(self, url, **kw):
        return self.request('GET', url, **kw)

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass


def _save_cookies(client, path):
    """Persist the cookie jar portably (curl_cffi's Cookies has no save())."""
    try:
        rows = [{'name': c.name, 'value': c.value, 'domain': c.domain,
                 'path': c.path, 'secure': bool(c.secure)}
                for c in client.session.cookies.jar]
        with open(path, 'w') as f:
            json.dump(rows, f)
    except Exception:
        pass


def _load_cookies(client, path):
    try:
        with open(path) as f:
            rows = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    for row in rows:
        try:
            client.session.cookies.set(
                row['name'], row['value'],
                domain=row.get('domain') or '', path=row.get('path') or '/')
        except Exception:
            pass


def fetch(url, method='GET', engine='chrome', proxy=None, geo_country=None,
          data=None, json_body=None, extra_headers=None, identity=None,
          cookie_file=None, timeout=30, in_place=True):
    """One-shot fetch. If cookie_file is given, load before and save after so a
    multi-call sequence keeps one session, cookie jar, and *identity* (so the
    UA/JA3 stay the same browser across calls, as a real session would)."""
    ident_path = (cookie_file + '.identity') if cookie_file else None
    if identity is None and ident_path:
        try:
            with open(ident_path) as f:
                identity = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            identity = None
    client = RawClient(engine=engine, proxy=proxy, geo_country=geo_country,
                       identity=identity, timeout=timeout)
    if ident_path and not identity:
        try:
            with open(ident_path, 'w') as f:
                json.dump(client.ident, f)
        except Exception:
            pass
    if cookie_file:
        _load_cookies(client, cookie_file)
    headers = extra_headers or None
    kw = {}
    if data is not None:
        kw['data'] = data
    if json_body is not None:
        kw['json'] = json_body
    t0 = time.time()
    r = client.request(method, url, headers=headers, **kw)
    elapsed = time.time() - t0
    if cookie_file:
        _save_cookies(client, cookie_file)
    out = {
        'identity': client.ident,
        'request': {'method': method, 'url': url, 'proxy': proxy},
        'status': r.status_code,
        'reason': r.reason,
        'elapsed_ms': int(elapsed * 1000),
        'headers': dict(r.headers),
        'body': r.text,
        'cookies': {c.name: c.value for c in client.session.cookies.jar},
    }
    client.close()
    return out


def probe(url='https://tls.peet.ws/api/all', engine='chrome', proxy=None,
          geo_country=None):
    """Ask a TLS-fingerprint endpoint what it sees — shows the JA3/JA4 + HTTP2
    fingerprint and the UA header, so you can confirm they're coherent."""
    out = fetch(url, engine=engine, proxy=proxy, geo_country=geo_country)
    parsed = None
    try:
        parsed = json.loads(out['body'])
    except Exception:
        pass
    return out, parsed
