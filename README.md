# ghostnet

<p align="center"><img src="assets/ghostnet.png" width="180" alt="ghostnet logo"></p>

<p align="center">
  <b>Anonymous device rotation for web application pentesting</b><br>
  fresh IP · fresh browser fingerprint · fresh session — on demand
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/version-1.0.0-46d746">
  <img alt="license" src="https://img.shields.io/badge/license-GPL--3.0-46d746">
  <img alt="platform" src="https://img.shields.io/badge/platform-Linux-lightgrey">
  <img alt="tor" src="https://img.shields.io/badge/transport-Tor%20%7C%20proxy%20%7C%20direct-46d746">
</p>

---

ghostnet turns one machine into many "devices" for testing how web applications track, rate-limit, and ban users. Each session gets a fresh browser profile (cookies, storage, fingerprint) and — optionally — a fresh public IP via Tor or your own proxy. When a session hits a limit, `gn new` continues as a brand-new user on the same site.

Built for **authorized pentesting**: rate-limit checks, trial/expiry controls, device- and IP-ban enforcement, anti-abuse logic.

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

## Install

```bash
git clone https://github.com/Sanjaya-Danushka/ghostnet.git
cd ghostnet
./install.sh
```

Requirements: Linux, `tor`, `curl`, Chrome (or Firefox via `--firefox`). Python deps install into a private venv automatically. **No root needed at runtime.**

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

Sites that block Tor datacenter IPs (Cloudflare-class) get automatic exit-IP retries (up to 5); if all exits are blocked, use `--transport direct` or your own proxy.

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

- `~/.config/ghostnet/` — tor config, control cookie, logs
- `~/.local/share/ghostnet/sessions/` — live browser profiles (deleted on rotate)
- `~/.local/share/ghostnet/log.jsonl` — rotation history (IP, fingerprint, timestamp)

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
