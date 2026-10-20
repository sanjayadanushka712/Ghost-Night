import random
from pathlib import Path

POOL = Path.home() / '.config' / 'ghost_night' / 'proxies.txt'


def load(path=None):
    p = Path(path) if path else POOL
    try:
        lines = p.read_text().splitlines()
    except FileNotFoundError:
        raise RuntimeError(
            f'proxy pool file not found: {p}\n'
            'create it with one proxy URL per line, e.g. socks5://user:pass@host:port')
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        out.append(ln)
    return out


def pick(path=None):
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
    p.write_text('\n'.join(entries) + '\n')
    return p
