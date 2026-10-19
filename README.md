# ghostnet

<p align="center"><img src="assets/ghostnet.png" width="180" alt="ghostnet logo"></p>

<p align="center">
  <b>Anonymous device rotation for web application pentesting</b><br>
  fresh IP · fresh browser fingerprint · fresh session — on demand
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/version-1.1.0-46d746">
  <img alt="license" src="https://img.shields.io/badge/license-GPL--3.0-46d746">
  <img alt="platform" src="https://img.shields.io/badge/platform-Linux-lightgrey">
  <img alt="tor" src="https://img.shields.io/badge/transport-Tor%20%7C%20proxy%20%7C%20direct-46d746">
</p>

---

ghostnet turns one machine into many "devices" for testing how web applications track, rate-limit, and ban users. Each session gets a fresh browser profile (cookies, storage, fingerprint) and — optionally — a fresh public IP via Tor or your own proxy. When a session hits a limit, `gn new` continues as a brand-new user on the same site.

Built for **authorized pentesting**: rate-limit checks, trial/expiry controls, device- and IP-ban enforcement, anti-abuse logic.

preview:https://drive.google.com/file/d/1VMZLD7_RlxjPKBVr9buRfhU_ZmayETO7/view?usp=sharing

<img width="606" height="295" alt="image" src="https://github.com/user-attachments/assets/d85010bd-1176-45dc-9e67-8c88f912d2b3" />


## What it defeats

| Signal apps use to track "you" | ghostnet countermeasure |
|---|---|
| Cookies / localStorage device IDs | brand-new browser profile every rotation — zero storage carryover |
| Public IP address | Tor circuit rotation (`NEWNYM`) or your own rotating proxy |
| WebRTC / DNS leaking the real IP | WebRTC policy locked off, DNS forced through the proxy |
| UA / locale / viewport / timezone | randomized per session |
| Canvas / WebGL fingerprint | deterministic-per-session noise (seeded) |

**Does not defeat:** commercial hardware-bound fingerprinting (FingerprintJS Pro-class) at high confidence, account-tied limits, TLS/JA3 correlation. MAC-address rotation is intentionally out of scope — MAC is Layer-2 and never reaches internet servers.

## Dependencies

| package | why | needed for |
|---|---|---|
| `tor` | IP rotation — new exit circuit per session (`NEWNYM`) | `--transport tor` (default) |
| `python3` (≥3.10) | runs ghostnet | everything |
| `curl` | checks real IP vs Tor exit IP | `gn verify`, exit-IP checks |
| Chrome or Chromium | the browser each session runs in (Firefox via `--firefox`) | sessions |
| `python-playwright` | drives the browser, injects per-session fingerprint | sessions — **installed automatically** into a private venv by `install.sh` |

Only **`tor` and `curl`** must be installed manually. Playwright is fetched into `~/.local/share/ghostnet/venv` by the installer — no system Python changes.

Manual install if you don't use `install.sh`:

```bash
# Arch
sudo pacman -S tor curl python google-chrome-stable   # or: chromium / firefox

# Debian / Ubuntu
sudo apt install tor curl python3 chromium            # or: firefox / google-chrome-stable

# Fedora
sudo dnf install tor curl python3 chromium            # or: firefox / google-chrome
```

then run `./install.sh` once (creates the venv + links the `gn` command), or set it up by hand:

```bash
python3 -m venv ~/.local/share/ghostnet/venv
~/.local/share/ghostnet/venv/bin/pip install playwright
ln -sf "$PWD/gn" ~/.local/bin/gn     # then ensure ~/.local/bin is in PATH
```

### Other requirements

- **A browser must be installed** — ghostnet uses your system Chrome/Chromium (default) or Firefox (`--firefox`); the installer warns if none is found.
- **`~/.local/bin` in PATH** — so the `gn` command resolves; installer prints the exact line if needed:
  `export PATH="$HOME/.local/bin:$PATH"` (add to `~/.bashrc` or `~/.zshrc`)
- **A desktop session** — headed (visible) browser windows need a display (X11/Wayland); `--headless` works without one.
- **Free local ports 19050/19051** — Tor's SOCKS and control ports (changed in `ghostnet/tor.py` if they clash).
- **Internet access** — to bootstrap Tor and load target sites; `install.sh` also downloads Playwright into the venv.

## Install

```bash
git clone https://github.com/Sanjaya-Danushka/ghostnet.git
cd ghostnet
./install.sh
```

**No root needed at runtime** — Tor runs as your user on ports 19050/19051; sudo is only used by the installer to place the `tor` package.

## Quick start

```bash
gn go https://target-site.com   # open as a fresh device; use it normally (log in, work)
                                # auto-stops when a limit message appears
gn new                          # continue as a brand-new user on the same site
gn status                       # tor, current session, recent events
gn verify                       # check tor (real ip vs exit ip)
gn off                          # stop everything, clean up
```

## Per-site behavior

Every app signals "you're out" differently — pick the mode that fits:

| site behavior | command |
|---|---|
| common limit text ("limit reached", "no credits", "upgrade to continue", ...) | `gn go URL` — generic watcher, stops itself |
| custom wording / modal / redirect | `gn go URL --detect "its wording"` — auto-rotates on match |
| silent block, no message | `gn go URL --no-watch` — plain sessions, rotate manually with `gn new` |
| timer-based trial | `gn go URL --every 25m` — rotate on a clock, before expiry |

Sites that block Tor datacenter IPs (Cloudflare-class) are handled by a built-in exit-strategy ladder — no VPN needed:

1. **proven exits** — exits that previously got HTTP 200 on this site are remembered (`~/.config/ghostnet/good_exits.json`) and pinned via `ExitNodes`
2. **country rotation** — cycles exit countries (US → DE → NL → FR → CA → SE → GB), since some pools are less aggressively blocked
3. **any exit** — unrestricted Tor
4. **direct fallback** — if every Tor strategy fails, switches to a direct connection and remembers it

Details of how the ladder stays fast and accurate:

- Strategy changes are applied via a **Tor config reload (SIGHUP, ~2s)** — no restart, no re-bootstrap
- `NEWNYM` is throttled to Tor's 10s rate limit, so page traffic never leaks through a stale circuit
- The proven exit is **verified against the live exit IP before the page loads**, so a blocked/not-blocked verdict is always accurate
- Exits that later get blocked are **auto-removed** from the proven list
- Once a good exit is cached, later runs connect on the first try

## All options

```bash
gn go URL --transport tor                    # default: tor with auto-retry on blocked exits
gn go URL --transport direct                 # no proxy — cookie/fingerprint rotation only
gn go URL --transport proxy --proxy socks5://127.0.0.1:1080
gn go URL --detect "regex"                   # custom limit pattern (auto-rotate on match)
gn go URL --no-watch                         # no limit watching at all
gn go URL --every 25m                        # timed rotation
gn go URL --once                             # single session
gn go URL --firefox --headless --keep-profiles
gn new --target https://other-site.com       # switch sites
```

## How a rotation works

1. Tor gets `NEWNYM` → next connection uses a new exit circuit (new public IP); blocked exits are retried automatically.
2. Old browser profile is closed and deleted.
3. A new profile is created with a fresh identity: new UA/platform, viewport, timezone, locale, canvas/WebGL noise seed.
4. The browser launches through the proxy and opens the target.
5. The event is logged (`~/.local/share/ghostnet/log.jsonl`) — evidence for your pentest report.

## Files

- `~/.config/ghostnet/` — tor config, control cookie, logs, proven-exit cache (`good_exits.json`)
- `~/.local/share/ghostnet/sessions/` — live browser profiles (deleted on rotate)
- `~/.local/share/ghostnet/log.jsonl` — rotation history (IP, fingerprint, timestamp)

## Changelog

### v1.1.0
- Self-contained IP rotation — no VPN needed
- Exit-strategy ladder: proven exits → country rotation → any exit → direct fallback
- Tor config changes applied via SIGHUP reload (~2s, no re-bootstrap)
- `NEWNYM` throttled to Tor's 10s rate limit — no stale-circuit leaks
- Proven exits pinned only for sites that actually blocked us (403/429)
- Blocked proven exits auto-removed from the cache
- Limit detection asks before rotating (`rotate to a new identity now? [y/N]`)
- Detects IP-keyed limits and explains why device rotation can't reset them
- `gn new` remembers transport/proxy from the last `gn go`
- Generic site-agnostic limit phrases; `--no-watch` / `--detect` / `--every` modes

### v1.0.0
- First release — fresh IP (Tor/proxy/direct) + fresh browser fingerprint per session
- Limit watcher, `gn go/new/status/verify/off`, JSONL evidence log, green terminal UI

## Contributing

Contributions welcome — this tool gets better with use:

- **Detection packs**: PRs with `--detect` patterns for known apps (helpful, no app-specific code in core)
- **Transports**: QUIC/HTTP3 proxies, WireGuard rotation, containerized exits
- **Fingerprinting**: stronger per-session noise, font/UA-CH consistency models, Firefox profile hardening
- **Ops**: better status views, JSON output mode, systemd units

Workflow: fork → feature branch → PR. Keep the core dependency-light (stdlib + playwright); no app-specific logic in core.

## License

[GPL-3.0](LICENSE) — free to use, modify, and redistribute under the same license.

## Disclaimer

Use ghostnet only against systems you are authorized to test. You are responsible for complying with applicable laws and each target's terms of service.
