import json
import random
import re
import shutil
import subprocess
import time
from pathlib import Path

SESSIONS = Path.home() / '.local' / 'share' / 'ghost_night' / 'sessions'

UA_OS = {
    'win': ('Windows NT 10.0; Win64; x64', 'Win32', 'Windows'),
    'mac': ('Macintosh; Intel Mac OS X 10_15_7', 'MacIntel', 'macOS'),
    'linux': ('X11; Linux x86_64', 'Linux x86_64', 'Linux'),
}

FF_OS = {
    'win': ('Windows NT 10.0; Win64; x64; rv:', 'Win32'),
    'mac': ('Macintosh; Intel Mac OS X 10.15; rv:', 'MacIntel'),
    'linux': ('X11; Linux x86_64; rv:', 'Linux x86_64'),
}

# coherent device bundles: OS + screen + dpr + viewport + timezone + locale +
# cores + memory + GPU must all describe ONE plausible machine
PROFILES = [
    dict(os='win', screen=(1920, 1080), dpr=1.0, viewport=(1600, 900),
         tz='America/New_York', locale='en-US', cores=16, memory=8, pv='15.0.0',
         gpu=('Google Inc. (NVIDIA)', 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)')),
    dict(os='win', screen=(1920, 1080), dpr=1.25, viewport=(1536, 864),
         tz='America/New_York', locale='en-US', cores=8, memory=8, pv='10.0.0',
         gpu=('Google Inc. (Intel)', 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)')),
    dict(os='win', screen=(1366, 768), dpr=1.0, viewport=(1366, 768),
         tz='Europe/Berlin', locale='de-DE', cores=4, memory=4, pv='10.0.0',
         gpu=('Google Inc. (Intel)', 'ANGLE (Intel, Intel(R) HD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)')),
    dict(os='win', screen=(2560, 1440), dpr=1.0, viewport=(1920, 1048),
         tz='Europe/London', locale='en-GB', cores=12, memory=16, pv='15.0.0',
         gpu=('Google Inc. (NVIDIA)', 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)')),
    dict(os='win', screen=(1920, 1080), dpr=1.0, viewport=(1600, 900),
         tz='America/Sao_Paulo', locale='pt-BR', cores=8, memory=8, pv='10.0.0',
         gpu=('Google Inc. (AMD)', 'ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)')),
    dict(os='mac', screen=(1440, 900), dpr=2.0, viewport=(1280, 800),
         tz='America/Los_Angeles', locale='en-US', cores=8, memory=8, pv='13.6.0',
         gpu=('Google Inc. (Apple)', 'ANGLE (Apple, Apple M1, OpenGL 4.1)')),
    dict(os='mac', screen=(1512, 982), dpr=2.0, viewport=(1356, 870),
         tz='Asia/Tokyo', locale='ja-JP', cores=10, memory=16, pv='14.4.1',
         gpu=('Google Inc. (Apple)', 'ANGLE (Apple, Apple M2, OpenGL 4.1)')),
    dict(os='mac', screen=(1680, 1050), dpr=2.0, viewport=(1440, 900),
         tz='Europe/Paris', locale='fr-FR', cores=8, memory=16, pv='12.7.4',
         gpu=('Google Inc. (Intel)', 'ANGLE (Intel, Intel(R) Iris(TM) Plus Graphics, OpenGL 4.1)')),
    dict(os='linux', screen=(1920, 1080), dpr=1.0, viewport=(1600, 900),
         tz='Europe/Berlin', locale='de-DE', cores=8, memory=16, pv='6.5.0',
         gpu=('Google Inc. (NVIDIA)', 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650, OpenGL 4.5.0)')),
    dict(os='linux', screen=(2560, 1440), dpr=1.0, viewport=(1920, 1032),
         tz='America/New_York', locale='en-US', cores=16, memory=32, pv='6.8.0',
         gpu=('Google Inc. (NVIDIA)', 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060, OpenGL 4.6.0)')),
    dict(os='linux', screen=(1920, 1080), dpr=1.0, viewport=(1600, 900),
         tz='Europe/Madrid', locale='es-ES', cores=6, memory=8, pv='6.2.0',
         gpu=('Google Inc. (Intel)', 'ANGLE (Intel, Mesa Intel(R) UHD Graphics 620 (KBL GT2), OpenGL 4.6 (Core Profile) Mesa 23.3.5)')),
    dict(os='linux', screen=(1366, 768), dpr=1.0, viewport=(1366, 768),
         tz='America/Sao_Paulo', locale='pt-BR', cores=4, memory=8, pv='5.15.0',
         gpu=('Google Inc. (AMD)', 'ANGLE (AMD, AMD Radeon RX 570 Series (navi14), OpenGL 4.6 (Core Profile) Mesa 23.2.1)')),
]

NOISE = r"""
(() => {
  const seed = __SEED__ >>> 0;
  const hash = (i) => {
    let h = (seed ^ i) >>> 0;
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
  const def = (obj, prop, value) => {
    try { Object.defineProperty(obj, prop, { get: () => value, configurable: true }); } catch (e) {}
  };
  def(navigator, 'platform', '__PLATFORM__');
  def(navigator, 'hardwareConcurrency', __CORES__);
  def(navigator, 'deviceMemory', __MEMORY__);
  def(Object.getPrototypeOf(navigator), 'webdriver', undefined);
  def(window, 'devicePixelRatio', __DPR__);
  const SW = __SW__, SH = __SH__, AVAIL_H = __AVAIL_H__;
  def(screen, 'width', SW);
  def(screen, 'availWidth', SW);
  def(screen, 'height', SH);
  def(screen, 'availHeight', AVAIL_H);
  def(screen, 'colorDepth', 24);
  def(screen, 'pixelDepth', 24);
  const VENDOR = '__VENDOR__', RENDERER = '__RENDERER__';
  for (const Ctx of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
    if (!Ctx) continue;
    const origParam = Ctx.prototype.getParameter;
    Ctx.prototype.getParameter = function (p) {
      if (p === 37445) return VENDOR;
      if (p === 37446) return RENDERER;
      return origParam.call(this, p);
    };
  }
  const origGet = CanvasRenderingContext2D.prototype.getImageData;
  CanvasRenderingContext2D.prototype.getImageData = function (x, y, w, h) {
    const img = origGet.call(this, x, y, w, h);
    const d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      if (hash(i) < 0.05) {
        d[i] = Math.min(255, d[i] + (hash(i + 1) < 0.5 ? 1 : 2));
      }
    }
    return img;
  };
})();
"""


def _real_browser_version(channel):
    exes = (['google-chrome-stable', 'google-chrome', 'chrome', 'chromium']
            if channel != 'firefox' else ['firefox'])
    for exe in exes:
        try:
            out = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=10).stdout
            m = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', out)
            if m:
                return m.group(0), m.group(1)
        except (OSError, subprocess.TimeoutExpired):
            continue
    return '131.0.0.0', '131'


def _script(profile, seed, version, channel):
    s = NOISE
    s = s.replace('__SEED__', str(seed))
    s = s.replace('__PLATFORM__', UA_OS[profile['os']][1])
    s = s.replace('__CORES__', str(profile['cores']))
    s = s.replace('__MEMORY__', str(profile['memory']))
    s = s.replace('__DPR__', str(profile['dpr']))
    sw, sh = profile['screen']
    avail = sh - (40 if profile['os'] != 'mac' else 24)
    s = s.replace('__SW__', str(sw)).replace('__SH__', str(sh))
    s = s.replace('__AVAIL_H__', str(avail))
    s = s.replace('__VENDOR__', profile['gpu'][0])
    s = s.replace('__RENDERER__', profile['gpu'][1])
    return s


class Manager:
    def __init__(self, headless=False, proxy=None, keep_profiles=False, channel='chrome'):
        self.headless = headless
        self.proxy = proxy
        self.keep = keep_profiles
        self.channel = channel
        self.pw = None
        self.context = None
        self._closed = True
        self.sid = None
        self.path = None
        self.started = None
        self.target = None

    def _pw(self):
        if self.pw is None:
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
        return self.pw

    def _attach_ua(self, ctx, page, ua, profile, version, locale):
        if self.channel == 'firefox':
            return
        major = version.split('.')[0]
        try:
            cdp = ctx.new_cdp_session(page)
            cdp.send('Network.setUserAgentOverride', {
                'userAgent': ua,
                'userAgentMetadata': {
                    'brands': [
                        {'brand': 'Not_A Brand', 'version': '8'},
                        {'brand': 'Chromium', 'version': major},
                        {'brand': 'Google Chrome', 'version': major},
                    ],
                    'fullVersionList': [
                        {'brand': 'Not_A Brand', 'version': '24.0.0.0'},
                        {'brand': 'Chromium', 'version': version},
                        {'brand': 'Google Chrome', 'version': version},
                    ],
                    'platform': UA_OS[profile['os']][2],
                    'platformVersion': profile['pv'],
                    'architecture': 'x86',
                    'model': '',
                    'mobile': False,
                    'bitness': '64',
                    'wow64': False,
                },
                'acceptLanguage': locale,
            })
        except Exception:
            pass
        try:
            ctx.on('page', lambda p: self._attach_ua(ctx, p, ua, profile, version, locale))
        except Exception:
            pass

    def open(self, target=None):
        self.close(delete=not self.keep)
        sid = f'{int(time.time())}-{random.randbytes(3).hex()}'
        path = SESSIONS / sid
        path.mkdir(parents=True, exist_ok=True)
        profile = random.choice(PROFILES)
        seed = random.getrandbits(32)
        version, major = _real_browser_version(self.channel)
        if self.channel == 'firefox':
            ua = ('Mozilla/5.0 (' + FF_OS[profile['os']][0] + major
                  + '.0) Gecko/20100101 Firefox/' + major + '.0')
        else:
            ua = ('Mozilla/5.0 (' + UA_OS[profile['os']][0]
                  + ') AppleWebKit/537.36 (KHTML, like Gecko) Chrome/'
                  + version + ' Safari/537.36')
        w, h = profile['viewport']
        kwargs = dict(
            user_data_dir=str(path),
            headless=self.headless,
            user_agent=ua,
            viewport={'width': w, 'height': h},
            device_scale_factor=profile['dpr'],
            locale=profile['locale'],
            timezone_id=profile['tz'],
            args=[
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled',
                '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
            ],
            ignore_default_args=['--enable-automation'],
        )
        if self.channel:
            kwargs['channel'] = self.channel
        if self.proxy:
            kwargs['proxy'] = {'server': self.proxy}
        ctx = self._pw().chromium.launch_persistent_context(**kwargs)
        self._closed = False
        ctx.on('close', lambda _: setattr(self, '_closed', True))
        ctx.add_init_script(_script(profile, seed, version, self.channel))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        self._attach_ua(ctx, page, ua, profile, version, profile['locale'])
        status = None
        if target:
            resp = page.goto(target, wait_until='domcontentloaded', timeout=60000)
            status = resp.status if resp else None
        self.context = ctx
        self.sid = sid
        self.path = path
        self.started = time.time()
        self.target = target
        meta = {
            'sid': sid, 'ua': ua, 'platform': UA_OS[profile['os']][1],
            'viewport': f'{w}x{h}', 'tz': profile['tz'], 'locale': profile['locale'],
            'gpu': profile['gpu'][1], 'cores': profile['cores'],
            'seed': seed, 'target': target, 'proxy': self.proxy,
            'status': status,
        }
        (path / 'ghost_night.json').write_text(json.dumps(meta))
        return meta

    def matches(self, pattern):
        import re
        if not self.context or not self.context.pages:
            return False
        try:
            html = self.context.pages[0].content()
        except Exception:
            return False
        return bool(re.search(pattern, html, re.I | re.S))

    def is_open(self):
        return bool(self.context and not self._closed)

    def close(self, delete=True):
        ctx, path = self.context, self.path
        self.context = None
        self.path = None
        self.sid = None
        self.started = None
        if ctx:
            try:
                ctx.close()
            except Exception:
                pass
        if delete and path and path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def stop(self):
        self.close(delete=not self.keep)
        if self.pw:
            try:
                self.pw.stop()
            except Exception:
                pass
            self.pw = None
