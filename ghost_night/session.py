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

# Firefox privacy-hardening prefs applied to every ephemeral profile — these
# make a throwaway Firefox look like a normal user while blocking the noisy
# surfaces (RFP stays OFF so we keep our own coherent spoof)
FF_PREFS = {
    'privacy.resistFingerprinting': False,
    'privacy.trackingprotection.enabled': True,
    'privacy.trackingprotection.fingerprinting.enabled': True,
    'privacy.trackingprotection.cryptomining.enabled': True,
    'privacy.firstparty.isolate': False,
    'webgl.disabled': False,
    'webgl.renderer-string-override': '',
    'webgl.vendor-string-override': '',
    'dom.webdriver.enabled': False,
    'useAutomationExtension': False,
    'media.navigator.enabled': True,
    'dom.webaudio.enabled': True,
    'beacon.enabled': True,
    'network.http.referer.XOriginPolicy': 0,
    'browser.startup.page': 0,
    'browser.startup.homepage_override.mstone': 'ignore',
    'datareporting.policy.dataSubmissionEnabled': False,
    'datareporting.healthreport.uploadEnabled': False,
    'toolkit.telemetry.enabled': False,
    'toolkit.telemetry.unified': False,
    'app.shield.optoutstudies.enabled': False,
    'browser.discovery.enabled': False,
    'browser.newtabpage.activity-stream.feeds.telemetry': False,
    'extensions.pocket.enabled': False,
    'signon.rememberSignons': False,
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

# coarse timezone -> country mapping used for cross-layer geo coherence:
# a Tor exit in Germany paired with an America/New_York profile is a tell, so
# when we know the exit country we prefer a profile whose tz sits in it
TZ_COUNTRY = {
    'America/New_York': 'US',
    'America/Los_Angeles': 'US',
    'Europe/Berlin': 'DE',
    'Europe/London': 'GB',
    'Europe/Paris': 'FR',
    'Europe/Madrid': 'ES',
    'Asia/Tokyo': 'JP',
    'America/Sao_Paulo': 'BR',
}


def _profile_country(profile):
    return TZ_COUNTRY.get(profile.get('tz'), 'US')


def pick(geo_country=None, exclude=None):
    """Pick a coherent profile, preferring one whose timezone fits the exit
    country when we know it (cross-layer geo coherence)."""
    pool = PROFILES
    if exclude:
        filtered = [p for p in PROFILES if p['os'] not in exclude]
        if filtered:
            pool = filtered
    if geo_country:
        geo_country = geo_country.upper()
        matching = [p for p in pool if _profile_country(p) == geo_country]
        if matching:
            pool = matching
    return random.choice(pool)

# plausible plugin/font sets per OS — a Windows profile that reports Linux
# fonts or zero plugins is an instant automation tell
FONTS = {
    'win': ['Arial', 'Arial Black', 'Bahnschrift', 'Calibri', 'Cambria', 'Cambria Math',
            'Candara', 'Comic Sans MS', 'Consolas', 'Constantia', 'Corbel', 'Courier New',
            'Ebrima', 'Franklin Gothic Medium', 'Gabriola', 'Gadugi', 'Georgia', 'Impact',
            'Ink Free', 'Javanese Text', 'Leelawadee UI', 'Lucida Console', 'Lucida Sans Unicode',
            'Malgun Gothic', 'Marlett', 'Microsoft Himalaya', 'Microsoft JhengHei',
            'Microsoft New Tai Lue', 'Microsoft PhagsPa', 'Microsoft Sans Serif',
            'Microsoft Tai Le', 'Microsoft YaHei', 'MingLiU-ExtB', 'Mongolian Baiti',
            'MS Gothic', 'MV Boli', 'Myanmar Text', 'Nirmala UI', 'Palatino Linotype',
            'Segoe MDL2 Assets', 'Segoe Print', 'Segoe Script', 'Segoe UI', 'Segoe UI Emoji',
            'SimSun', 'Sitka', 'Sylfaen', 'Symbol', 'Tahoma', 'Times New Roman',
            'Trebuchet MS', 'Verdana', 'Webdings', 'Wingdings', 'Yu Gothic'],
    'mac': ['American Typewriter', 'Andale Mono', 'Apple Chancery', 'Apple Color Emoji',
            'Apple Symbols', 'Arial', 'Arial Black', 'Arial Narrow', 'Arial Rounded MT Bold',
            'Avenir', 'Avenir Next', 'Ayuthaya', 'Baskerville', 'Big Caslon', 'Bodoni 72',
            'Bradley Hand', 'Brush Script MT', 'Chalkboard', 'Chalkduster', 'Charter', 'Cochin',
            'Comic Sans MS', 'Copperplate', 'Courier New', 'Didot', 'Futura', 'Geneva',
            'Georgia', 'Gill Sans', 'Helvetica', 'Helvetica Neue', 'Herculanum', 'Hoefler Text',
            'Impact', 'Lucida Grande', 'Luminari', 'Marker Felt', 'Menlo', 'Monaco',
            'Noteworthy', 'Optima', 'Palatino', 'Papyrus', 'Phosphate', 'Rage Italic',
            'Rockwell', 'Savoye LET', 'SignPainter', 'Skia', 'Snell Roundhand', 'Tahoma',
            'Times New Roman', 'Trattatello', 'Trebuchet MS', 'Verdana', 'Zapfino'],
    'linux': ['Arial', 'Bitstream Charter', 'Cantarell', 'Century Schoolbook L', 'Comic Sans MS',
              'Courier 10 Pitch', 'Courier New', 'DejaVu Sans', 'DejaVu Sans Mono', 'DejaVu Serif',
              'Dingbats', 'FreeMono', 'FreeSans', 'FreeSerif', 'Georgia', 'Impact',
              'Liberation Mono', 'Liberation Sans', 'Liberation Serif', 'Loma', 'Nimbus Mono PS',
              'Nimbus Roman', 'Nimbus Sans', 'Noto Color Emoji', 'Noto Sans', 'Noto Serif',
              'P052', 'Standard Symbols PS', 'Tahoma', 'Terminus', 'Times New Roman',
              'Trebuchet MS', 'Ubuntu', 'Ubuntu Condensed', 'Ubuntu Mono', 'URW Bookman',
              'URW Gothic', 'Verdana', 'Z003'],
}

PLUGINS = {
    'win': [('PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
            ('Chrome PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
            ('Chromium PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
            ('Microsoft Edge PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
            ('WebKit built-in PDF', 'internal-pdf-viewer', 'Portable Document Format')],
    'mac': [('PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
            ('Chrome PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
            ('Chromium PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
            ('WebKit built-in PDF', 'internal-pdf-viewer', 'Portable Document Format')],
    'linux': [('PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
              ('Chrome PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
              ('Chromium PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format')],
}

# Firefox's plugin set is genuinely different from Chrome's — reusing Chrome's
# names on a Firefox UA is itself a tell. Modern Firefox reports only its
# internal PDF viewer.
FF_PLUGINS = {
    'win': [('PDF.js', 'internal-pdf-viewer', 'Portable Document Format')],
    'mac': [('PDF.js', 'internal-pdf-viewer', 'Portable Document Format')],
    'linux': [('PDF.js', 'internal-pdf-viewer', 'Portable Document Format')],
    'android': [('PDF.js', 'internal-pdf-viewer', 'Portable Document Format')],
}

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
  const defineFn = (obj, prop, fn) => {
    try { Object.defineProperty(obj, prop, { get: fn, configurable: true }); } catch (e) {}
  };
  const ENGINE = '__ENGINE__';
  def(navigator, 'platform', '__PLATFORM__');
  def(navigator, 'hardwareConcurrency', __CORES__);
  def(window, 'devicePixelRatio', __DPR__);
  const SW = __SW__, SH = __SH__, AVAIL_H = __AVAIL_H__;
  def(screen, 'width', SW);
  def(screen, 'availWidth', SW);
  def(screen, 'height', SH);
  def(screen, 'availHeight', AVAIL_H);
  def(screen, 'colorDepth', 24);
  def(screen, 'pixelDepth', 24);

  // --- automation leaks ---
  // fully remove webdriver from both navigator and its prototype chain
  try { delete Navigator.prototype.webdriver; } catch (e) {}
  try { delete navigator.webdriver; } catch (e) {}
  try {
    Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver',
      { get: () => undefined, configurable: true });
    delete Object.getPrototypeOf(navigator).webdriver;
  } catch (e) {}
  def(navigator, 'languages', ['__LOCALE__', '__LOCALE_BASE__']);
  if (ENGINE === 'firefox') {
    // Firefox-specific coherent surface:
    //  - navigator.vendor is the empty string
    //  - deviceMemory does NOT exist (leave it undefined)
    //  - window.chrome does NOT exist (adding it is a Chrome tell)
    //  - buildID / oscpu are Firefox-only fingerprintable props
    def(navigator, 'vendor', '');
    try { delete navigator.deviceMemory; } catch (e) {}
    try { delete window.chrome; } catch (e) {}
  } else {
    def(navigator, 'vendor', '__VENDOR_NS__');
    def(navigator, 'deviceMemory', __MEMORY__);
    // window.chrome runtime shim (headless Chromium omits it)
    if (!window.chrome) { window.chrome = {}; }
    if (!window.chrome.runtime) {
      window.chrome.runtime = {
        connect: function () { return { onMessage: { addListener: function () {} },
          postMessage: function () {}, disconnect: function () {} }; },
        sendMessage: function () {}, id: undefined,
      };
    }
    if (!window.chrome.app) { window.chrome.app = { isInstalled: false, InstallState: {}, RunningState: {} }; }
    if (!window.chrome.csi) { window.chrome.csi = function () { return {}; }; }
    if (!window.chrome.loadTimes) { window.chrome.loadTimes = function () { return {}; }; }
  }

  // --- plugins (mimeType array consistent with the OS/engine) ---
  const PLUGINS = __PLUGINS__;
  function mkPlugin(name, filename, desc) {
    // Build plugin/mime as plain own-property objects. Using the native
    // Plugin/MimeType prototypes makes their getters throw "Illegal
    // invocation" when read on a non-native object; the array types still
    // report [object PluginArray]/[object MimeTypeArray] below.
    const defOwn = (o, k, v) => Object.defineProperty(o, k,
      { value: v, writable: true, enumerable: true, configurable: true });
    const p = {};
    defOwn(p, 'name', name); defOwn(p, 'filename', filename); defOwn(p, 'description', desc);
    Object.defineProperty(p, Symbol.toStringTag, { value: 'Plugin', configurable: true });
    const mime = {};
    defOwn(mime, 'type', 'application/pdf');
    defOwn(mime, 'suffixes', 'pdf');
    defOwn(mime, 'description', desc);
    defOwn(mime, 'enabledPlugin', p);
    Object.defineProperty(mime, Symbol.toStringTag, { value: 'MimeType', configurable: true });
    defOwn(p, 'length', 1);
    defOwn(p, '0', mime);
    defOwn(p, 'item', (i) => (i === 0 ? mime : null));
    defOwn(p, 'namedItem', (t) => (t === mime.type ? mime : null));
    return { plugin: p, mimes: [mime] };
  }
  function buildPlugins() {
    const arr = []; const mime = [];
    for (const [n, f, d] of PLUGINS) {
      const { plugin, mimes } = mkPlugin(n, f, d);
      arr.push(plugin); mime.push(...mimes);
    }
    const arrProto = Object.create(PluginArray.prototype);
    const mimeSet = Object.create(MimeTypeArray.prototype);
    mime.forEach((m, i) => { mimeSet[i] = m; });
    Object.defineProperty(mimeSet, 'length', { value: mime.length, enumerable: false });
    mimeSet.item = (i) => mime[i] || null;
    mimeSet.namedItem = (t) => mime.find((m) => m.type === t) || null;
    arr.forEach((p, i) => { arrProto[i] = p; });
    Object.defineProperty(arrProto, 'length', { value: arr.length, enumerable: false });
    arrProto.item = (i) => arr[i] || null;
    arrProto.namedItem = (n) => arr.find((p) => p.name === n) || null;
    arrProto.refresh = () => {};
    if (ENGINE === 'firefox') {
      Object.defineProperty(arrProto, Symbol.iterator, { value: function () {
        let i = 0; const items = arr;
        return { next: () => (i < items.length ? { value: items[i++], done: false }
          : { value: undefined, done: true }) };
      }, configurable: true });
      Object.defineProperty(mimeSet, Symbol.iterator, { value: function () {
        let i = 0; const items = mime;
        return { next: () => (i < items.length ? { value: items[i++], done: false }
          : { value: undefined, done: true }) };
      }, configurable: true });
    }
    return { plugins: arrProto, mimeTypes: mimeSet };
  }
  const P = buildPlugins();
  def(navigator, 'plugins', P.plugins);
  def(navigator, 'mimeTypes', P.mimeTypes);
  if (ENGINE !== 'firefox') { def(navigator, 'pdfViewerEnabled', true); }

  // --- permissions: notifications default must be 'prompt' not 'denied' ---
  if (navigator.permissions && navigator.permissions.query) {
    const origQ = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (p) => {
      if (p && p.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission, name: 'notifications',
          onchange: null });
      }
      return origQ(p);
    };
  }

  // --- fonts: report exactly the profile OS's font list, block the host's ---
  const FONTS = __FONTS__;
  const fontSet = new Set(FONTS.map((f) => f.toLowerCase()));
  const baseSet = new Set(['serif', 'sans-serif', 'monospace', 'cursive',
    'fantasy', 'system-ui', '-apple-system', 'ui-sans-serif', 'ui-serif', 'ui-monospace']);
  const firstFamily = (spec) => {
    let s = String(spec).split(',')[0].trim().replace(/["']/g, '');
    s = s.replace(/^[\d.]+(px|pt|em|rem|%|ex|ch|vw|vh|vh)?\s*/i, '');
    s = s.replace(/^(italic|oblique|normal|small-caps|bold|bolder|lighter|\d00)\s*/i, '');
    return s.trim();
  };
  const unknown = (fam) => {
    const f = String(fam).trim().toLowerCase();
    if (!f) { return false; }
    return !baseSet.has(f) && !fontSet.has(f);
  };
  if (document.fonts && document.fonts.check) {
    document.fonts.check = function (font, text) {
      return !unknown(firstFamily(font));
    };
  }
  // CSS masking: define a (broken) @font-face for every font the profile OS
  // should NOT have. Once a family is declared via @font-face, Chrome stops
  // falling back to the host's system font of that name and instead uses the
  // broken face -> the probe's family resolves to the next in the list
  // (usually the generic fallback), so its width is unchanged -> "absent".
  const hostOnly = __HOST_ONLY__;
  const _applyFontMask = () => {
    if (!hostOnly.length || document.getElementById('__gn_fontmask__')) { return true; }
    const root = document.head || document.documentElement;
    if (!root) { return false; }
    try {
      const css = hostOnly.map((f) =>
        '@font-face{font-family:"' + f + '";'
        + 'src:url(data:font/woff;base64,AAAA) format("woff")}'
      ).join('');
      const st = document.createElement('style');
      st.id = '__gn_fontmask__';
      st.textContent = css;
      root.appendChild(st);
      return true;
    } catch (e) { return false; }
  };
  if (!_applyFontMask()) {
    // document_start: no <head>/<html> yet — attach as soon as one exists,
    // before any page script can run its font probe
    const obs = new MutationObserver(() => {
      if (_applyFontMask()) { obs.disconnect(); }
    });
    try {
      obs.observe(document, { childList: true, subtree: true });
    } catch (e) {
      document.addEventListener('readystatechange', _applyFontMask);
    }
  }

  // --- WebGL: keep the spoofed vendor/renderer (already set below) ---
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

  // --- WebGPU: spoof the adapter so GPU stack matches the profile ---
  const WGPU_VENDOR = '__WGPU_VENDOR__', WGPU_ARCH = '__WGPU_ARCH__';
  if (navigator.gpu && navigator.gpu.requestAdapter) {
    const origReq = navigator.gpu.requestAdapter.bind(navigator.gpu);
    navigator.gpu.requestAdapter = async function (opts) {
      const adapter = await origReq(opts);
      if (adapter && adapter.info !== undefined) {
        try {
          Object.defineProperty(adapter, 'info', {
            get: () => ({ vendor: WGPU_VENDOR, architecture: WGPU_ARCH,
              device: '', description: '' }), configurable: true });
        } catch (e) {}
      }
      if (adapter && adapter.requestAdapterInfo) {
        try { adapter.requestAdapterInfo = async () => ({ vendor: WGPU_VENDOR,
          architecture: WGPU_ARCH, device: '', description: '' }); } catch (e) {}
      }
      return adapter;
    };
  }

  // --- audio: deterministic-per-session AudioContext fingerprint noise ---
  if (window.AudioBuffer) {
    const origGetChannel = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function (ch) {
      const data = origGetChannel.call(this, ch);
      for (let i = 0; i < data.length; i++) {
        if (hash(i) < 0.01) {
          data[i] = data[i] + (hash(i + 7) - 0.5) * 1e-7;
        }
      }
      return data;
    };
  }
  if (window.AnalyserNode && AnalyserNode.prototype.getFloatFrequencyData) {
    const origGetFreq = AnalyserNode.prototype.getFloatFrequencyData;
    AnalyserNode.prototype.getFloatFrequencyData = function (arr) {
      origGetFreq.call(this, arr);
      for (let i = 0; i < arr.length; i++) {
        if (hash(i + 3) < 0.02) { arr[i] = arr[i] + (hash(i + 11) - 0.5) * 1e-4; }
      }
    };
  }

  // --- canvas noise (kept) ---
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
    if channel == 'firefox':
        exes = ['firefox', 'firefox-developer-edition',
                str(Path.home() / '.cache' / 'ms-playwright')]
        ff_bin = _playwright_firefox_bin()
        for exe in ([ff_bin] if ff_bin else []) + ['firefox', 'firefox-developer-edition']:
            try:
                out = subprocess.run([exe, '--version'], capture_output=True,
                                     text=True, timeout=10).stdout
                m = re.search(r'Firefox[\s/](\d+)\.(\d+)', out, re.I)
                if m:
                    return f'{m.group(1)}.0', m.group(1)
            except (OSError, subprocess.TimeoutExpired):
                continue
        return '133.0', '133'
    exes = ['google-chrome-stable', 'google-chrome', 'chrome', 'chromium']
    for exe in exes:
        try:
            out = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=10).stdout
            m = re.search(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', out)
            if m:
                return m.group(0), m.group(1)
        except (OSError, subprocess.TimeoutExpired):
            continue
    return '131.0.0.0', '131'


def _playwright_firefox_bin():
    root = Path.home() / '.cache' / 'ms-playwright'
    try:
        for d in sorted(root.glob('firefox-*'), reverse=True):
            for cand in (d / 'firefox' / 'firefox', d / 'firefox' / 'firefox-bin'):
                if cand.exists():
                    return str(cand)
    except OSError:
        pass
    return None


def _host_only_fonts(profile):
    """fonts the host has that the profile OS should not report"""
    profile_fonts = {f.lower() for f in FONTS[profile['os']]}
    out = set()
    for os_fonts in FONTS.values():
        for f in os_fonts:
            if f.lower() not in profile_fonts:
                out.add(f)
    return sorted(out)


def _wgpu_info(profile):
    g = profile['gpu'][1].lower()
    if 'nvidia' in g:
        vendor = 'nvidia'
    elif 'amd' in g or 'radeon' in g:
        vendor = 'amd'
    elif 'intel' in g:
        vendor = 'intel'
    elif 'apple' in g:
        vendor = 'apple'
    else:
        vendor = 'nvidia'
    if 'rtx 40' in g or 'rtx 30' in g:
        arch = 'ampere' if 'rtx 30' in g else 'ada'
    elif 'radeon' in g or 'navi' in g:
        arch = 'rdna2'
    elif 'm1' in g:
        arch = 'apple'
    elif 'm2' in g:
        arch = 'apple'
    elif 'iris' in g or 'uhd' in g or 'hd graphics' in g:
        arch = 'gen-9'
    elif 'gtx' in g:
        arch = 'turing' if 'gtx 16' in g else 'pascal'
    else:
        arch = 'ampere'
    return vendor, arch


def _script(profile, seed, version, channel):
    s = NOISE
    is_ff = channel == 'firefox'
    s = s.replace('__SEED__', str(seed))
    s = s.replace('__ENGINE__', 'firefox' if is_ff else 'chrome')
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
    s = s.replace('__VENDOR_NS__', 'Google Inc.' if profile['os'] != 'mac' else 'Apple Computer, Inc.')
    s = s.replace('__LOCALE__', profile['locale'])
    s = s.replace('__LOCALE_BASE__', profile['locale'].split('-')[0])
    s = s.replace('__FONTS__', json.dumps(FONTS[profile['os']]))
    s = s.replace('__HOST_ONLY__', json.dumps(_host_only_fonts(profile)))
    plug = (FF_PLUGINS if is_ff else PLUGINS)[profile['os']]
    s = s.replace('__PLUGINS__', json.dumps(plug))
    wv, wa = _wgpu_info(profile)
    s = s.replace('__WGPU_VENDOR__', wv)
    s = s.replace('__WGPU_ARCH__', wa)
    return s


class Manager:
    def __init__(self, headless=False, proxy=None, keep_profiles=False, channel='chrome',
                 geo_country=None):
        self.headless = headless
        self.proxy = proxy
        self.keep = keep_profiles
        self.channel = channel
        self.geo_country = geo_country
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
        profile = pick(geo_country=self.geo_country)
        seed = random.getrandbits(32)
        version, major = _real_browser_version(self.channel)
        is_ff = self.channel == 'firefox'
        if is_ff:
            rv = major if '.' in str(major) else f'{major}.0'
            ua = ('Mozilla/5.0 (' + FF_OS[profile['os']][0] + rv
                  + ') Gecko/20100101 Firefox/' + rv)
            plat = FF_OS[profile['os']][1]
        else:
            ua = ('Mozilla/5.0 (' + UA_OS[profile['os']][0]
                  + ') AppleWebKit/537.36 (KHTML, like Gecko) Chrome/'
                  + version + ' Safari/537.36')
            plat = UA_OS[profile['os']][1]
        w, h = profile['viewport']
        kwargs = dict(
            user_data_dir=str(path),
            headless=self.headless,
            user_agent=ua,
            viewport={'width': w, 'height': h},
            device_scale_factor=profile['dpr'],
            locale=profile['locale'],
            timezone_id=profile['tz'],
        )
        if is_ff:
            prefs = dict(FF_PREFS)
            prefs['general.useragent.override'] = ua
            prefs['intl.accept_languages'] = (
                profile['locale'] + ',' + profile['locale'].split('-')[0])
            kwargs['firefox_user_prefs'] = prefs
        else:
            kwargs['args'] = [
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled',
                '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
            ]
            kwargs['ignore_default_args'] = ['--enable-automation']
            if self.channel:
                kwargs['channel'] = self.channel
        if self.proxy:
            kwargs['proxy'] = {'server': self.proxy}
        engine = self._pw().firefox if is_ff else self._pw().chromium
        ctx = engine.launch_persistent_context(**kwargs)
        self._closed = False
        ctx.on('close', lambda _: setattr(self, '_closed', True))
        ctx.add_init_script(_script(profile, seed, version, self.channel))
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not is_ff:
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
            'sid': sid, 'ua': ua, 'platform': plat,
            'viewport': f'{w}x{h}', 'tz': profile['tz'], 'locale': profile['locale'],
            'gpu': profile['gpu'][1], 'cores': profile['cores'],
            'seed': seed, 'target': target, 'proxy': self.proxy,
            'status': status, 'engine': 'firefox' if is_ff else 'chromium',
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

    # --- human-like interaction (opt-in via gn go --human) ---

    def _ease(self, p):
        # ease-in-out cubic — non-linear speed, unlike teleporting bots
        return 4 * p * p * p if p < 0.5 else 1 - pow(-2 * p + 2, 3) / 2

    def human_mouse(self, page, x, y, steps=None):
        import math
        try:
            start = page.evaluate("() => ({x: window.__gn_mx || 0, y: window.__gn_my || 0})")
        except Exception:
            start = {'x': 0, 'y': 0}
        x0, y0 = float(start.get('x', 0)), float(start.get('y', 0))
        dist = math.hypot(x - x0, y - y0)
        steps = steps or max(6, min(40, int(dist / 12)))
        # a bowed path, not a straight line, with per-step jitter
        cx = (x0 + x) / 2 + random.uniform(-dist * 0.15, dist * 0.15)
        cy = (y0 + y) / 2 + random.uniform(-dist * 0.15, dist * 0.15)
        for i in range(1, steps + 1):
            t = self._ease(i / steps)
            bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x
            by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y
            jx = bx + random.uniform(-1.2, 1.2)
            jy = by + random.uniform(-1.2, 1.2)
            page.mouse.move(jx, jy)
            page.evaluate('(p) => { window.__gn_mx = p.x; window.__gn_my = p.y; }',
                          {'x': jx, 'y': jy})
            time.sleep(random.uniform(0.008, 0.028))
        page.evaluate('(p) => { window.__gn_mx = p.x; window.__gn_my = p.y; }',
                      {'x': x, 'y': y})

    def human_click(self, page, selector):
        try:
            el = page.query_selector(selector)
            if not el:
                return False
            box = el.bounding_box()
            if not box:
                el.click()
                return True
            tx = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            ty = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            self.human_mouse(page, tx, ty)
            time.sleep(random.uniform(0.05, 0.2))
            page.mouse.down()
            time.sleep(random.uniform(0.04, 0.12))
            page.mouse.up()
            return True
        except Exception:
            return False

    def human_type(self, page, selector, text):
        try:
            el = page.query_selector(selector)
            if not el:
                return False
            el.click()
        except Exception:
            return False
        for ch in text:
            # real key events (down/up) so keydown/keyup listeners fire, like typing
            page.keyboard.type(ch, delay=0)
            time.sleep(random.uniform(0.04, 0.16))
            if random.random() < 0.08:
                time.sleep(random.uniform(0.2, 0.7))
        return True

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
