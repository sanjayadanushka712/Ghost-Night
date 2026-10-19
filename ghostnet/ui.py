import os
import sys

from . import __version__

GREEN = '\033[38;5;46m'
BRIGHT = '\033[1;38;5;118m'
NEON = '\033[38;5;154m'
DIM = '\033[38;5;242m'
YELLOW = '\033[38;5;220m'
RED = '\033[38;5;203m'
RESET = '\033[0m'
BOLD = '\033[1m'


def _tty():
    return sys.stdout.isatty() and not os.environ.get('NO_COLOR')


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
    print(c(GREEN, '  ➜ ') + msg)


def ok(msg):
    print(c(GREEN, '  ✔ ') + msg)


def info(msg):
    print(c(DIM, '  » ') + msg)


def warn(msg):
    print(c(YELLOW, '  ! ') + msg)


def err(msg):
    print(c(RED, '  ✘ ') + msg, file=sys.stderr)


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
    inner = max((len(k) + 2 + len(str(v)) for k, v, _ in rows), default=40)
    width = max(52, inner)
    print(c(GREEN, f'  ┌─ {title} ') + c(GREEN, '─' * max(0, width - len(title) - 4) + '┐'))
    for key, value, color in rows:
        pad = max(0, width - 2 - len(key) - len(str(value)))
        print(
            c(GREEN, '  │ ') + c(DIM, key.ljust(12))
            + (c(color, str(value)) if color else str(value))
            + ' ' * pad + c(GREEN, ' │')
        )
    print(c(GREEN, '  └' + '─' * width + '┘'))
