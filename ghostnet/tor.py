import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

CONF = Path.home() / '.config' / 'ghostnet'
DATA = CONF / 'data'
TORRC = CONF / 'torrc'
PIDFILE = CONF / 'tor.pid'
LOG = CONF / 'tor.log'
SOCKS_HOST, SOCKS_PORT = '127.0.0.1', 19050
CTRL_HOST, CTRL_PORT = '127.0.0.1', 19051


def _ensure():
    DATA.mkdir(parents=True, exist_ok=True)


def bootstrap_done():
    try:
        return 'Bootstrapped 100%' in LOG.read_text()
    except FileNotFoundError:
        return False


def write_config(exit_nodes=None, strict=False, obfs4=False, bridges=None):
    _ensure()
    lines = [
        f'SocksPort {SOCKS_HOST}:{SOCKS_PORT}',
        f'ControlPort {CTRL_HOST}:{CTRL_PORT}',
        'CookieAuthentication 1',
        f'CookieAuthFile {DATA}/control_auth_cookie',
        f'DataDirectory {DATA}',
        f'Log notice file {LOG}',
        'ClientOnly 1',
        'AvoidDiskWrites 1',
    ]
    if obfs4:
        import shutil
        exe = shutil.which('obfs4proxy')
        if not exe:
            raise RuntimeError('obfs4proxy not installed (arch: yay -S obfs4proxy)')
        lines.append(f'ClientTransportPlugin obfs4 exec {exe}')
        lines.append('UseBridges 1')
        for b in (bridges or []):
            b = b.strip()
            if b and not b.startswith('Bridge '):
                lines.append('Bridge ' + b)
            elif b:
                lines.append(b)
    if exit_nodes:
        toks = []
        for e in exit_nodes:
            e = e.strip()
            if e.count('.') == 3 and e.replace('.', '').isdigit():
                toks.append(e)
            else:
                toks.append('{' + e + '}')
        lines.append('ExitNodes ' + ','.join(toks))
        if strict:
            lines.append('StrictNodes 1')
    new = '\n'.join(lines) + '\n'
    old = TORRC.read_text() if TORRC.exists() else None
    changed = new != old
    if changed:
        TORRC.write_text(new)
    return changed


def is_running():
    if not PIDFILE.exists():
        return False
    try:
        os.kill(int(PIDFILE.read_text().strip()), 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def _reload():
    try:
        os.kill(int(PIDFILE.read_text().strip()), signal.SIGHUP)
        time.sleep(2)
        try:
            newnym()
        except Exception:
            pass
        return True
    except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
        return False


def start(timeout=120, exit_nodes=None, strict=False, obfs4=False, bridges=None):
    old = TORRC.read_text() if TORRC.exists() else ''
    old_obfs4 = 'UseBridges 1' in old
    changed = write_config(exit_nodes, strict, obfs4, bridges)
    if is_running() and bootstrap_done():
        if changed:
            if old_obfs4 != bool(obfs4):
                stop()
                time.sleep(1)
            else:
                _reload()
                return
        else:
            return
    if is_running():
        stop()
        time.sleep(1)
    LOG.unlink(missing_ok=True)
    with open(LOG, 'a') as err:
        p = subprocess.Popen(
            ['tor', '-f', str(TORRC)],
            stdout=subprocess.DEVNULL,
            stderr=err,
            start_new_session=True,
        )
    PIDFILE.write_text(str(p.pid))
    deadline = time.time() + timeout
    while time.time() < deadline:
        if p.poll() is not None:
            raise RuntimeError(f'tor exited (code {p.returncode}); see {LOG}')
        if bootstrap_done():
            return
        time.sleep(0.5)
    raise TimeoutError(f'tor bootstrap timed out; see {LOG}')


def stop():
    if PIDFILE.exists():
        try:
            os.kill(int(PIDFILE.read_text().strip()), signal.SIGTERM)
        except (ValueError, ProcessLookupError):
            pass
        PIDFILE.unlink(missing_ok=True)


def _control(cmds):
    cookie = (DATA / 'control_auth_cookie').read_bytes()
    s = socket.create_connection((CTRL_HOST, CTRL_PORT), timeout=10)
    s.settimeout(10)
    f = s.makefile('rb')

    def xmit(cmd):
        s.sendall((cmd + '\r\n').encode())
        replies = []
        while True:
            raw = f.readline()
            if not raw:
                raise ConnectionError('control socket closed')
            text = raw.decode(errors='replace').rstrip('\r\n')
            if not text:
                continue
            replies.append(text)
            if len(text) >= 4 and text[3] == ' ':
                if text.startswith('250'):
                    return replies
                raise RuntimeError(f'control error: {text}')

    try:
        xmit('AUTHENTICATE ' + cookie.hex())
        out = []
        for cmd in cmds:
            out.extend(xmit(cmd))
        return out
    finally:
        s.close()


_LAST_NEWNYM = 0.0


def newnym():
    global _LAST_NEWNYM
    wait = 11.0 - (time.time() - _LAST_NEWNYM)
    if wait > 0:
        time.sleep(wait)
    _control(['SIGNAL NEWNYM'])
    _LAST_NEWNYM = time.time()


def socks_proxy():
    return f'socks5://{SOCKS_HOST}:{SOCKS_PORT}'


def get_ip(timeout=25):
    r = subprocess.run(
        ['curl', '-s', '--max-time', str(timeout),
         '--socks5-hostname', f'{SOCKS_HOST}:{SOCKS_PORT}',
         'https://check.torproject.org/api/ip'],
        capture_output=True, text=True,
    )
    try:
        d = json.loads(r.stdout)
        return d.get('IP'), bool(d.get('IsTor'))
    except json.JSONDecodeError:
        return None, None


def real_ip(timeout=10):
    r = subprocess.run(
        ['curl', '-s', '--max-time', str(timeout), 'https://api.ipify.org'],
        capture_output=True, text=True,
    )
    return r.stdout.strip() or None
