import os
import sys
import threading
import time
from contextlib import contextmanager

from . import __version__

GREEN = '\033[38;5;46m'
BRIGHT = '\033[1;38;5;118m'
NEON = '\033[38;5;154m'
DIM = '\033[38;5;242m'
YELLOW = '\033[38;5;220m'
RED = '\033[38;5;203m'
RESET = '\033[0m'
BOLD = '\033[1m'

_QUIET = False


def set_quiet(on):
    global _QUIET
    _QUIET = bool(on)


def _tty():
    return sys.stdout.isatty() and not os.environ.get('NO_COLOR') and not _QUIET


def c(color, text):
    return f'{color}{text}{RESET}' if _tty() else str(text)


def banner():
    if not _tty():
        return
    print()
    print(c(GREEN, '  ╭──────────────────────────────────────────────╮'))
    print(c(GREEN, '  │ ') + c(BRIGHT, '██╗  ██╗ ██████╗ ███████╗███████╗███████╗███████╗') + c(GREEN, ' │'))
    print(c(GREEN, '  │ ') + c(BRIGHT, '██║  ██║██╔═══██╗██╔════╝██╔════╝██╔════╝██╔════╝') + c(GREEN, ' │'))
    print(c(GREEN, '  │ ') + c(BRIGHT, '███████║██║   ██║███████╗█████╗  ███████╗███████╗') + c(GREEN, ' │'))
    print(c(GREEN, '  │ ') + c(BRIGHT, '██╔══██║██║   ██║╚════██║██╔══╝  ╚════██║╚════██║') + c(GREEN, ' │'))
    print(c(GREEN, '  │ ') + c(BRIGHT, '██║  ██║╚██████╔╝███████║███████╗███████║███████║') + c(GREEN, ' │'))
    print(c(GREEN, '  │ ') + c(BRIGHT, '╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝') + c(GREEN, ' │'))
    print(c(GREEN, '  │ ') + c(DIM, f'   fresh ip · fresh device · every time  v{__version__}') + c(GREEN, ' │'))
    print(c(GREEN, '  ╰──────────────────────────────────────────────╯'))
    print()


def step(msg):
    if _QUIET:
        return
    print(c(GREEN, '  ➜ ') + msg)


def ok(msg):
    if _QUIET:
        return
    print(c(GREEN, '  ✔ ') + msg)


def info(msg):
    if _QUIET:
        return
    print(c(DIM, '  » ') + msg)


def warn(msg):
    if _QUIET:
        return
    print(c(YELLOW, '  ! ') + msg)


def err(msg):
    print(c(RED, '  ✘ ') + msg, file=sys.stderr)


@contextmanager
def spinner(label):
    """Animated 'label...' line that runs until the block exits."""
    if _QUIET:
        yield
        return
    if not sys.stdout.isatty():
        info(label)
        yield
        return
    stop = threading.Event()

    def frames():
        i = 0
        while not stop.is_set():
            dots = '.' * (1 + i % 3)
            sys.stdout.write('\r  ' + c(DIM, f'{label}{dots}'))
            sys.stdout.flush()
            i += 1
            stop.wait(0.4)

    t = threading.Thread(target=frames, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=1)
        sys.stdout.write('\r' + ' ' * (len(label) + 8) + '\r')
        sys.stdout.flush()


def session_line(meta):
    print(
        c(GREEN, '  ● ') + c(BRIGHT, meta['sid'])
        + c(DIM, f"   {meta['platform']} · {meta['viewport']} · {meta['tz']} · {meta['locale']}")
    )


def ip_line(ip):
    print(c(DIM, '    ip  ') + c(BRIGHT, ip))


def kv(key, value, color=None):
    val = c(color, value) if color else str(value)
    print(f'  {c(DIM, key.ljust(12))} {val}')


def panel(title, rows):
    inner = max((14 + len(str(v)) for _, v, _ in rows), default=40)
    width = max(52, inner)
    print(c(GREEN, f'  ┌─ {title} ') + c(GREEN, '─' * max(0, width - len(title) - 4) + '┐'))
    for key, value, color in rows:
        pad = max(0, width - 16 - len(str(value)))
        print(
            c(GREEN, '  │ ') + c(DIM, key.ljust(12))
            + (c(color, str(value)) if color else str(value))
            + ' ' * pad + c(GREEN, ' │')
        )
    print(c(GREEN, '  └' + '─' * width + '┘'))
