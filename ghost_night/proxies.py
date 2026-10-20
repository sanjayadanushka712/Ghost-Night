import random
import re
from pathlib import Path

POOL = Path.home() / '.config' / 'ghost_night' / 'proxies.txt'

# a pool line may carry an optional ISO-2 country tag so the browser profile's
# timezone/locale can be matched to that proxy's geography:
#   socks5://host:1080 cc=DE
#   socks5://host:1080|DE
_TAG_RE = re.compile(r'^(?P<url>\S+?)(?:\s+cc=(?P<cc1>[A-Za-z]{2})|\|(?P<cc2>[A-Za-z]{2}))?$')


def parse(line):
    """Return (url, country|None) for a pool line."""
    m = _TAG_RE.match(line.strip())
    if not m:
        return line.strip(), None
    url = m.group('url')
    cc = m.group('cc1') or m.group('cc2')
    return url, (cc.upper() if cc else None)


def load(path=None):
    p = Path(path) if path else POOL
    try:
        lines = p.read_text().splitlines()
    except FileNotFoundError:
        raise RuntimeError(
            f'proxy pool file not found: {p}\n'
            'create it with one proxy URL per line, e.g. socks5://user:pass@host:port\n'
            'optionally tag a country for geo coherence: socks5://host:1080 cc=DE')
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        out.append(parse(ln))
    return out


def pick(path=None):
    """Return (url, country|None) chosen at random from the pool."""
    entries = load(path)
    if not entries:
        raise RuntimeError(f'proxy pool is empty: {path or POOL}')
    return random.choice(entries)


def available(path=None):
    try:
        return len(load(path)) > 0
    except RuntimeError:
        return False


def save(entries, path=None):
    p = Path(path) if path else POOL
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for e in entries:
        if isinstance(e, (tuple, list)) and len(e) == 2 and e[1]:
            lines.append(f'{e[0]} cc={e[1]}')
        else:
            lines.append(e if isinstance(e, str) else e[0])
    p.write_text('\n'.join(lines) + '\n')
    return p
