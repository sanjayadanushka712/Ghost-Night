import json
import random
import shutil
import time
from pathlib import Path

SESSIONS = Path.home() / '.local' / 'share' / 'ghostnet' / 'sessions'

UAS = [
    ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Win32'),
    ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'MacIntel'),
    ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Linux x86_64'),
    ('Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0', 'Win32'),
    ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0', 'Linux x86_64'),
    ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0', 'MacIntel'),
]
VIEWPORTS = [(1920, 1080), (1536, 864), (1366, 768), (1440, 900), (1280, 800), (1600, 900)]
TIMEZONES = ['UTC', 'America/New_York', 'Europe/Berlin', 'Europe/London', 'Asia/Tokyo', 'Australia/Sydney', 'America/Los_Angeles']
LOCALES = ['en-US', 'en-GB', 'de-DE', 'fr-FR', 'ja-JP', 'es-ES', 'pt-BR']

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
  if (typeof WebGLRenderingContext !== 'undefined') {
    const origParam = WebGLRenderingContext.prototype.getParameter;
    const UNMASKED = 37445;
    WebGLRenderingContext.prototype.getParameter = function (p) {
      const v = origParam.call(this, p);
      if (p === UNMASKED && typeof v === 'string') {
        return Array.from(v).map((c, i) =>
          String.fromCharCode(Math.max(32, c.charCodeAt(0) + (hash(i) < 0.3 ? 1 : 0)))
        ).join('');
      }
      return v;
    };
  }
})();
"""


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

    def open(self, target=None):
        self.close(delete=not self.keep)
        sid = f'{int(time.time())}-{random.randbytes(3).hex()}'
        path = SESSIONS / sid
        path.mkdir(parents=True, exist_ok=True)
        ua, platform = random.choice(UAS)
        w, h = random.choice(VIEWPORTS)
        tz = random.choice(TIMEZONES)
        locale = random.choice(LOCALES)
        seed = random.getrandbits(32)
        kwargs = dict(
            user_data_dir=str(path),
            headless=self.headless,
            user_agent=ua,
            viewport={'width': w, 'height': h},
            locale=locale,
            timezone_id=tz,
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
        ctx.add_init_script(NOISE.replace('__SEED__', str(seed)))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if target:
            page.goto(target, wait_until='domcontentloaded', timeout=60000)
        self.context = ctx
        self.sid = sid
        self.path = path
        self.started = time.time()
        self.target = target
        meta = {
            'sid': sid, 'ua': ua, 'platform': platform,
            'viewport': f'{w}x{h}', 'tz': tz, 'locale': locale,
            'seed': seed, 'target': target, 'proxy': self.proxy,
        }
        (path / 'ghostnet.json').write_text(json.dumps(meta))
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
