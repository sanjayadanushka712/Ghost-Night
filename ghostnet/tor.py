import json
import os
import signal
import socket
import struct
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


def write_config():
    _ensure()
    TORRC.write_text(
        f'SocksPort {SOCKS_HOST}:{SOCKS_PORT}\n'
        f'ControlPort {CTRL_HOST}:{CTRL_PORT}\n'
        f'CookieAuthentication 1\n'
        f'CookieAuthFile {DATA}/control_auth_cookie\n'
        f'DataDirectory {DATA}\n'
        f'Log notice file {LOG}\n'
        f'ClientOnly 1\n'
        f'AvoidDiskWrites 1\n'
    )


def is_running():
    if not PIDFILE.exists():
        return False
    try:
        os.kill(int(PIDFILE.read_text().strip()), 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def start(timeout=120):
    if is_running() and bootstrap_done():
        return
    if is_running():
        stop()
        time.sleep(1)
    write_config()
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
    f = s.makefile('rb')

    def xmit(cmd):
        data = cmd.encode() if isinstance(cmd, str) else cmd
        s.sendall(struct.pack('>I', len(data)) + data)
        replies = []
        while True:
            header = f.read(4)
            if len(header) < 4:
                raise ConnectionError('control socket closed')
            body = f.read(struct.unpack('>I', header)[0])
            for line in body.decode(errors='replace').split('\r\n'):
                if not line:
                    continue
                replies.append(line)
                if len(line) >= 4 and line[3] == ' ':
                    if line.startswith('250'):
                        return replies
                    raise RuntimeError(f'control error: {line}')

    try:
        xmit(b'AUTHENTICATE ' + cookie.hex().encode())
        out = []
        for cmd in cmds:
            out.extend(xmit(cmd))
        return out
    finally:
        s.close()


def newnym():
    _control(['SIGNAL NEWNYM'])


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
