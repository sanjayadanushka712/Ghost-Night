import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from . import session, tor, ui
from .log import event, tail

CONF = Path.home() / '.config' / 'ghostnet'
GN_PID = CONF / 'gn.pid'
STATE = CONF / 'state.json'
GOOD_EXITS = CONF / 'good_exits.json'
COUNTRY_POOL = ['us', 'de', 'nl', 'fr', 'ca', 'se', 'gb']
DEFAULT_DETECT = (
    r'limit\s*(?:hit|reached|exceeded)|'
    r'you(?:\x27|’)?(?:ve| have)?\s*(?:reached|exceeded)\s+(?:your\s+)?(?:limit|quota)|'
    r'(?:no|out of|no remaining)\s+credits|'
    r'upgrade (?:your subscription|to continue)|'
    r'quota exceeded|usage limit|rate limit|too many requests|'
    r'free trial (?:ended|expired)|credits?\s+(?:exceeded|exhausted)|'
    r'payment required|no (?:more|remaining) (?:tries|attempts|uses)'
)


def parse_every(s):
    s = str(s).strip().lower()
    units = {'s': 1, 'm': 60, 'h': 3600}
    if s and s[-1] in units:
        return int(float(s[:-1]) * units[s[-1]])
    return int(s)


def _save_state(**kw):
    CONF.mkdir(parents=True, exist_ok=True)
    data = json.loads(STATE.read_text()) if STATE.exists() else {}
    data.update(kw)
    STATE.write_text(json.dumps(data, indent=2))


def _proxy_for(args):
    if args.transport == 'direct':
        return None
    if args.transport == 'proxy':
        if not args.proxy:
            sys.exit('error: --transport proxy requires --proxy URL (e.g. socks5://127.0.0.1:1080)')
        return args.proxy
    tor.start()
    return tor.socks_proxy()


def _good_exits():
    try:
        return json.loads(GOOD_EXITS.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _remember_good(host, ip):
    if not host or not ip:
        return
    CONF.mkdir(parents=True, exist_ok=True)
    g = _good_exits()
    lst = g.get(host) or []
    if ip in lst:
        lst.remove(ip)
    lst.insert(0, ip)
    g[host] = lst[:10]
    GOOD_EXITS.write_text(json.dumps(g, indent=2))


def _open_with_retry(mgr, args):
    if args.transport != 'tor':
        return mgr.open(args.target)

    host = urlparse(args.target).hostname or args.target
    good = (_good_exits().get(host) or [])[:3]
    strategies = []
    if good:
        strategies.append((good, True, 'proven exits ' + ','.join(good)))
    for c in COUNTRY_POOL:
        strategies.append(([c], True, f'exit country {c.upper()}'))
    strategies.append((None, False, 'any exit'))

    meta = None
    for nodes, strict, label in strategies:
        if nodes is not None or label == 'any exit':
            ui.info(f'tor: trying {label}')
            tor.start(exit_nodes=nodes, strict=strict)
        meta = mgr.open(args.target)
        blocked = meta.get('status') in (403, 429) or mgr.matches(r'Error: Forbidden|Access denied|403 Forbidden')
        if not blocked:
            if nodes is not None:
                ui.ok(f'connected via {label}')
            ip = tor.get_ip()[0]
            _remember_good(host, ip)
            return meta
        ip = None
        try:
            ip = tor.get_ip()[0]
        except Exception:
            pass
        ui.warn(f'blocked (HTTP {meta.get("status")}) via {label}' + (f' — exit {ip}' if ip else ''))

    ui.warn('all tor exit strategies blocked — falling back to direct connection (no proxy)')
    mgr.proxy = None
    args.transport = 'direct'
    return mgr.open(args.target)


def _run_session_loop(args, once=False):
    CONF.mkdir(parents=True, exist_ok=True)
    GN_PID.write_text(str(os.getpid()))

    def on_term(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, on_term)
    proxy = _proxy_for(args)
    mgr = session.Manager(headless=args.headless, proxy=proxy, keep_profiles=args.keep_profiles)
    state = {'last': time.time()}

    def rotate(reason):
        if args.transport == 'tor':
            tor.newnym()
            time.sleep(2)
        meta = _open_with_retry(mgr, args)
        state['last'] = time.time()
        ip = tor.get_ip()[0] if args.transport == 'tor' else None
        _save_state(sid=meta['sid'], target=args.target, since=state['last'], proxy=proxy,
                    reason=reason, ip=ip, transport=args.transport)
        event('rotate', reason=reason, sid=meta['sid'], target=args.target, ip=ip,
              viewport=meta['viewport'], tz=meta['tz'], platform=meta['platform'])
        ui.session_line(meta)
        if ip:
            ui.ip_line(ip)

    interval = parse_every(args.every) if args.every else None
    if getattr(args, 'no_watch', False):
        watch = None
    else:
        watch = args.detect if args.detect else (DEFAULT_DETECT if not once else None)
    instant_limits = 0
    rotate('start')
    if once:
        return mgr, rotate, state

    try:
        while True:
            time.sleep(5)
            if not mgr.is_open():
                rotate('browser-closed')
                continue
            if interval and time.time() - state['last'] >= interval:
                ui.info(f'timer fired after {args.every} — rotating')
                rotate('timer')
                continue
            if watch and mgr.matches(watch):
                if args.detect:
                    ui.info(f'pattern matched ({args.detect}) — rotating')
                    rotate('detected')
                else:
                    ui.warn('limit message detected')
                    if time.time() - state['last'] < 30:
                        instant_limits += 1
                        if instant_limits >= 2:
                            ui.warn('limit returns instantly on every fresh session — it is keyed to your IP, not the device')
                            ui.info('device rotation cannot reset it; use a different IP: --transport proxy --proxy <vpn-socks-url>')
                    else:
                        instant_limits = 0
                    try:
                        ans = input(ui.c(ui.GREEN, '  rotate to a new identity now? [y/N] ')).strip().lower()
                    except EOFError:
                        ans = ''
                    if ans in ('y', 'yes'):
                        ui.info('rotating to a new identity')
                        rotate('limit-prompt')
                        continue
                    ui.info("session closed — run 'gn new' to continue as a brand-new user")
                    break
    except KeyboardInterrupt:
        print()
        ui.info('stopping')
    finally:
        mgr.stop()
        GN_PID.unlink(missing_ok=True)
        _save_state(sid=None, since=None)


def cmd_go(args):
    if not args.target.startswith(('http://', 'https://', 'file://')):
        sys.exit('error: target must be a full URL (https://...)')
    ui.banner()
    ui.step(f'{ui.c(ui.BOLD, args.target)}   ' + ui.c(ui.DIM, f'transport={args.transport}'))
    if args.once and not args.every and not args.detect:
        mgr, _, _ = _run_session_loop(args, once=True)
        ui.info('single session running — close the browser window or Ctrl+C to exit')
        try:
            while mgr.is_open():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            mgr.stop()
            GN_PID.unlink(missing_ok=True)
        return
    _run_session_loop(args)


def cmd_new(args):
    CONF.mkdir(parents=True, exist_ok=True)
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    target = args.target or st.get('target')
    if not target:
        sys.exit("error: no previous target — run 'gn go URL' first, or pass --target")
    args.target = target
    args.transport = args.transport or st.get('transport') or 'tor'
    if args.transport == 'proxy' and not args.proxy:
        args.proxy = st.get('proxy')
    proxy = _proxy_for(args)
    if args.transport == 'tor':
        tor.newnym()
        time.sleep(2)
    mgr = session.Manager(headless=args.headless, proxy=proxy, channel='chrome' if not args.firefox else 'firefox')
    meta = _open_with_retry(mgr, args)
    ip = tor.get_ip()[0] if args.transport == 'tor' else None
    _save_state(sid=meta['sid'], target=target, since=time.time(), proxy=proxy,
                reason='manual', ip=ip, transport=args.transport)
    event('rotate', reason='manual', sid=meta['sid'], target=target, ip=ip,
          viewport=meta['viewport'], tz=meta['tz'], platform=meta['platform'])
    ui.step('new user on ' + ui.c(ui.BOLD, target))
    ui.session_line(meta)
    if ip:
        ui.ip_line(ip)
    if args.headless:
        mgr.stop()
        return
    ui.info('close the browser window or Ctrl+C to exit')
    try:
        while mgr.is_open():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        mgr.stop()
        GN_PID.unlink(missing_ok=True)


def cmd_status(args):
    if tor.is_running():
        pid = tor.PIDFILE.read_text().strip()
        boot = 'done' if tor.bootstrap_done() else 'in progress'
        tor_row = (f'running · pid {pid} · bootstrap {boot}', ui.GREEN)
    else:
        tor_row = ('stopped', ui.DIM)
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    n = len(list(session.SESSIONS.glob('*'))) if session.SESSIONS.exists() else 0
    loop = f"running · pid {GN_PID.read_text().strip()}" if GN_PID.exists() else 'not running'
    ui.panel('ghostnet', [
        ('tor', tor_row[0], tor_row[1]),
        ('session', st.get('sid') or '-', ui.BRIGHT if st.get('sid') else None),
        ('target', st.get('target') or '-', None),
        ('exit ip', st.get('ip') or '-', ui.BRIGHT if st.get('ip') else None),
        ('loop', loop, ui.GREEN if GN_PID.exists() else ui.DIM),
        ('profiles', n, None),
    ])
    events = tail(5)
    if events:
        ui.info('recent events')
        for e in events:
            print(ui.c(ui.DIM, '   ') + json.dumps(e))


def cmd_verify(args):
    real = tor.real_ip()
    ui.step('real ip        ' + ui.c(ui.BRIGHT, str(real)))
    if not tor.is_running():
        ui.info('starting tor...')
        tor.start()
    ip, is_tor = tor.get_ip()
    ui.step('tor exit ip    ' + ui.c(ui.BRIGHT, str(ip)))
    if is_tor:
        ui.ok('tor verified — traffic is going through the tor network')
    else:
        ui.warn('tor not verified')
    if ip and real and ip == real:
        ui.err('exit ip equals real ip — traffic is NOT going through tor')


def cmd_off(args):
    killed = False
    if GN_PID.exists():
        try:
            os.kill(int(GN_PID.read_text().strip()), signal.SIGTERM)
            killed = True
        except (ValueError, ProcessLookupError):
            pass
        GN_PID.unlink(missing_ok=True)
        time.sleep(1)
    subprocess.run(['pkill', '-f', str(session.SESSIONS)], capture_output=True)
    if session.SESSIONS.exists() and not args.keep_profiles:
        shutil.rmtree(session.SESSIONS, ignore_errors=True)
        session.SESSIONS.mkdir(parents=True, exist_ok=True)
    tor.stop()
    STATE.unlink(missing_ok=True)
    ui.ok(
        f"off — {'loop stopped, ' if killed else ''}browsers closed, "
        f"profiles {'kept' if args.keep_profiles else 'removed'}, tor stopped"
    )


def main(argv=None):
    p = argparse.ArgumentParser(
        prog='gn',
        description='ghostnet — anonymous device rotation: fresh IP + fresh browser fingerprint per session',
    )
    sub = p.add_subparsers(dest='cmd', required=True)

    go = sub.add_parser('go', help='start rotating sessions on a target (the main command)')
    go.add_argument('target', help='target URL')
    go.add_argument('--every', help='auto-rotate on interval, e.g. 25m, 90s, 1h')
    go.add_argument('--detect', help='regex watched on the page; rotate when it matches')
    go.add_argument('--no-watch', action='store_true', help='disable limit-message watching (plain fresh sessions)')
    go.add_argument('--transport', choices=['tor', 'proxy', 'direct'], default='tor')
    go.add_argument('--proxy', help='custom proxy URL for --transport proxy')
    go.add_argument('--headless', action='store_true', help='run browser without window')
    go.add_argument('--once', action='store_true', help='single session, no auto-rotate loop')
    go.add_argument('--keep-profiles', action='store_true', help='do not delete profiles on rotate')
    go.add_argument('--firefox', action='store_true', help='use Firefox channel instead of Chrome')
    go.set_defaults(func=cmd_go)

    new = sub.add_parser('new', help='one-shot: new IP + fresh device session')
    new.add_argument('--target', default=None, help='URL to open')
    new.add_argument('--transport', choices=['tor', 'proxy', 'direct'], default=None,
                     help='default: remember what "gn go" used (else tor)')
    new.add_argument('--proxy', help='custom proxy URL for --transport proxy')
    new.add_argument('--headless', action='store_true')
    new.add_argument('--firefox', action='store_true')
    new.set_defaults(func=cmd_new)

    st = sub.add_parser('status', help='show current state')
    st.set_defaults(func=cmd_status)

    ver = sub.add_parser('verify', help='check tor connection and exit ip')
    ver.set_defaults(func=cmd_verify)

    off = sub.add_parser('off', help='stop everything and clean up')
    off.add_argument('--keep-profiles', action='store_true')
    off.set_defaults(func=cmd_off)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print()
        ui.info('stopped')
    except Exception as e:
        ui.err(f'{type(e).__name__}: {e}')
        sys.exit(1)
