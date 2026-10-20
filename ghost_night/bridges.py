import base64
import json
import shutil
import urllib.request
from pathlib import Path

CONF = Path.home() / '.config' / 'ghost_night'
BRIDGES = CONF / 'bridges.txt'
CAPTCHA = CONF / 'captcha.jpg'
MOAT = 'https://bridges.torproject.org/moat'
HEADERS = {'Content-Type': 'application/vnd.api+json'}


def _post(path, payload, timeout=25):
    req = urllib.request.Request(
        MOAT + path, data=json.dumps(payload).encode(),
        headers=HEADERS, method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def load():
    if not BRIDGES.exists():
        return []
    return [ln.strip() for ln in BRIDGES.read_text().splitlines()
            if ln.strip() and not ln.startswith('#')]


def _routable(bridge):
    """drop moat junk like private-IP bridges — they can never connect"""
    import ipaddress
    parts = bridge.split()
    if len(parts) < 2 or ':' not in parts[1]:
        return True
    host = parts[1].rsplit(':', 1)[0].strip('[]')
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def save(lines):
    CONF.mkdir(parents=True, exist_ok=True)
    lines = [b for b in lines if _routable(b)]
    have = set(load())
    fresh = [b for b in lines if b and b not in have]
    if fresh:
        with open(BRIDGES, 'a') as f:
            for b in fresh:
                f.write(b.strip() + '\n')
    return load()


def available():
    return shutil.which('obfs4proxy') is not None and bool(load())


def fetch_interactive():
    """moat captcha flow: challenge -> human solves -> bridges. Returns bridge lines."""
    if not shutil.which('obfs4proxy'):
        raise RuntimeError('obfs4proxy not installed (arch: yay -S obfs4proxy)')
    data = _post('/fetch', {'data': [{
        'type': 'client-transports', 'version': '0.1.0', 'supported': ['obfs4'],
    }]})
    items = data.get('data') or []
    ch = items[0] if items else {}
    if 'challenge' not in ch or 'image' not in ch:
        raise RuntimeError('moat did not return a captcha challenge')
    img = ch['image']
    if img.startswith('data:'):
        img = img.split(',', 1)[1]
    CONF.mkdir(parents=True, exist_ok=True)
    CAPTCHA.write_bytes(base64.b64decode(img))
    print(f'  captcha saved: {CAPTCHA}')
    print('  open it, type the text you see:')
    try:
        subprocess_open(CAPTCHA)
    except Exception:
        pass
    solution = input('  captcha > ').strip()
    if not solution:
        raise RuntimeError('no solution given')
    res = _post('/check', {'data': [{
        'type': 'moat-solution', 'id': '2', 'version': '0.1.0',
        'transport': 'obfs4',
        'challenge': ch['challenge'], 'solution': solution, 'qrcode': 'false',
    }]})
    CAPTCHA.unlink(missing_ok=True)
    got = [b for b in (res.get('data') or [{}])[0].get('bridges') or [] if b.startswith('obfs4')]
    if not got:
        raise RuntimeError('captcha rejected or no bridges returned — try again')
    save(got)
    return load()


def subprocess_open(path):
    import subprocess
    subprocess.Popen(['xdg-open', str(path)], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
