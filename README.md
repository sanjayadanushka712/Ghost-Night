# Gray Net

<p align="center"><img src="assets/gray_net.png" width="180" alt="Gray Net logo"></p>

<p align="center">
  <b>Anonymous device rotation for web application pentesting</b><br>
  fresh IP · fresh browser fingerprint · fresh session — on demand
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/version-1.3.0-46d746">
  <img alt="license" src="https://img.shields.io/badge/license-GPL--3.0-46d746">
  <img alt="platform" src="https://img.shields.io/badge/platform-Linux-lightgrey">
  <img alt="tor" src="https://img.shields.io/badge/transport-Tor%20%7C%20obfs4%20%7C%20proxy%20%7C%20direct-46d746">
</p>

---

Gray Net turns one machine into many "devices" for testing how web applications track, rate-limit, and ban users. Each session gets a fresh browser profile (cookies, storage, fingerprint) and — optionally — a fresh public IP via Tor or your own proxy. When a session hits a limit, `gn new` continues as a brand-new user on the same site.

Built for **authorized pentesting**: rate-limit checks, trial/expiry controls, device- and IP-ban enforcement, anti-abuse logic.

<img width="606" height="295" alt="image" src="https://github.com/user-attachments/assets/d85010bd-1176-45dc-9e67-8c88f912d2b3" />

## Demo

🎥 **Watch the walkthrough:** [Gray Net demo video](https://drive.google.com/file/d/1VMZLD7_RlxjPKBVr9buRfhU_ZmayETO7/view?usp=sharing)

## What it defeats

| Signal apps use to track "you" | Gray Net countermeasure |
|---|---|
| Cookies / localStorage device IDs | brand-new browser profile every rotation — zero storage carryover |
| Public IP address | Tor circuit rotation (`NEWNYM`) or your own rotating proxy |
| WebRTC / DNS leaking the real IP | WebRTC policy locked off, DNS forced through the proxy |
| UA / locale / viewport / timezone | **coherent device profile** — one plausible machine (OS, screen, dpr, cores, GPU, tz+locale all match), browser version = your real installed version (UA ↔ UA-CH can't disagree) |
| Canvas / WebGL fingerprint | deterministic-per-session canvas noise + WebGL vendor/renderer spoofed to match the profile's GPU |
| Cross-API contradictions (the #1 bot signal) | `navigator.platform`, `userAgentData`, screen size, `devicePixelRatio`, `hardwareConcurrency`, `deviceMemory` all overridden to the same profile |

**Does not defeat:** server-side, non-browser signals — account-tied limits, IP reputation of datacenter exits, TLS/JA3 correlation, behavioral typing. Against fingerprint-script services (FingerprintJS open-source / "device fingerprint" scripts) Gray Net's coherent profiles are strong: every API tells the same story. Hardware-bound commercial stacking (FingerprintJS Pro-class with server-side ML) can still correlate — no single browser-side tool beats that honestly. MAC-address rotation is intentionally out of scope — MAC is Layer-2 and never reaches internet servers.

## Security & privacy

- **Local-only** — Gray Net has no server, no telemetry, no phone-home. Everything (state, logs, profiles) stays in `~/.config/gray_net/` and `~/.local/share/gray_net/`.
- **Profiles are deleted on rotation** — each browser profile (cookies, storage) is wiped when the next identity starts; use `--keep-profiles` only if you need forensic artifacts.
- **Evidence log may contain sensitive data** — `log.jsonl` records IPs, fingerprints, and timestamps of your sessions. Treat it like test evidence: don't share it publicly, delete it when the engagement ends (`gn off` clears state, remove the log manually if needed).
- **Tor exit nodes can read unencrypted traffic** — never send passwords, tokens, or personal data over plain `http://` through Tor. HTTPS is encrypted end-to-end even via exits.
- **Gray Net does not anonymize YOU against the network operator** — your ISP/employer can see you're using Tor; Tor traffic itself is visible (though content is encrypted). Use `--transport obfs4` to make Tor traffic indistinguishable from random encrypted bytes on the wire (ISP DPI can't tell it's Tor). For full anonymity against the network operator use a VPN/Tails — not this tool.
- **Fingerprint spoofing is best-effort** — coherent profiles defeat casual cross-session tracking and fingerprint scripts; a motivated adversary with server-side signals (FingerprintJS Pro-class) is still a stronger opponent.

## Dependencies

| package | why | needed for |
|---|---|---|
| `tor` | IP rotation — new exit circuit per session (`NEWNYM`) | `--transport tor` (default) |
| `obfs4proxy` (optional) | pluggable transport — Tor traffic disguised as random bytes, so your ISP can't see you're using Tor | `--transport obfs4` |
| `python3` (≥3.10) | runs Gray Net | everything |
| `curl` | checks real IP vs Tor exit IP | `gn verify`, exit-IP checks |
| Chrome or Chromium | the browser each session runs in (Firefox via `--firefox`) | sessions |
| `python-playwright` | drives the browser, injects per-session fingerprint | sessions — **installed automatically** into a private venv by `install.sh` |

Only **`tor` and `curl`** must be installed manually. Playwright is fetched into `~/.local/share/gray_net/venv` by the installer — no system Python changes.

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
python3 -m venv ~/.local/share/gray_net/venv
~/.local/share/gray_net/venv/bin/pip install playwright
ln -sf "$PWD/gn" ~/.local/bin/gn     # then ensure ~/.local/bin is in PATH
```

### Other requirements

- **A browser must be installed** — Gray Net uses your system Chrome/Chromium (default) or Firefox (`--firefox`); the installer warns if none is found.
- **`~/.local/bin` in PATH** — so the `gn` command resolves; installer prints the exact line if needed:
  `export PATH="$HOME/.local/bin:$PATH"` (add to `~/.bashrc` or `~/.zshrc`)
- **A desktop session** — headed (visible) browser windows need a display (X11/Wayland); `--headless` works without one.
- **Free local ports 19050/19051** — Tor's SOCKS and control ports (changed in `gray_net/tor.py` if they clash).
- **Internet access** — to bootstrap Tor and load target sites; `install.sh` also downloads Playwright into the venv.

## Install

```bash
git clone https://github.com/Sanjaya-Danushka/gray-net.git
cd gray-net
./install.sh
```

**No root needed at runtime** — Tor runs as your user on ports 19050/19051; sudo is only used by the installer to place the `tor` package.

## Quick start

```bash
gn go https://target-site.com   # open as a fresh device; use it normally (log in, work)
                                # auto-stops when a limit message appears
gn go https://target-site.com --detach
                                # same, but in the background — your prompt returns
                                # control it live: gn new / gn status / gn off
gn new                          # continue as a brand-new user on the same site
                                # (if a loop is running, it rotates that loop — no Ctrl+C needed)
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

1. **proven exits** — exits that previously got HTTP 200 on this site are remembered (`~/.config/gray_net/good_exits.json`) and pinned via `ExitNodes`
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
gn go URL --transport obfs4                  # tor over obfs4 bridges — ISP can't see it's tor
gn go URL --transport direct                 # no proxy — cookie/fingerprint rotation only
gn go URL --transport proxy --proxy socks5://127.0.0.1:1080
gn go URL --detect "regex"                   # custom limit pattern (auto-rotate on match)
gn go URL --no-watch                         # no limit watching at all
gn go URL --every 25m                        # timed rotation
gn go URL --once                             # single session
gn go URL --detach                           # background loop; control with gn new/status/off
gn go URL --firefox --headless --keep-profiles
gn new --target https://other-site.com       # switch sites
```

## How a rotation works

1. Tor gets `NEWNYM` → next connection uses a new exit circuit (new public IP); blocked exits are retried automatically.
2. Old browser profile is closed and deleted.
3. A new profile is created with a fresh identity: one coherent device profile (OS + screen + dpr + GPU + cores + tz + locale all from the same plausible machine), real browser version, fresh canvas noise seed.
4. The browser launches through the proxy and opens the target.
5. The event is logged (`~/.local/share/gray_net/log.jsonl`) — evidence for your pentest report.

## Files

- `~/.config/gray_net/` — tor config, control cookie, logs, proven-exit cache (`good_exits.json`), obfs4 bridges (`bridges.txt`)
- `~/.local/share/gray_net/sessions/` — live browser profiles (deleted on rotate)
- `~/.local/share/gray_net/log.jsonl` — rotation history (IP, fingerprint, timestamp)

## Changelog

### v1.3.0
- **Coherent device profiles** — every session picks one plausible machine (OS, screen, dpr, viewport, GPU, cores, memory, timezone+locale pairs) instead of mixing random values that contradict each other
- **UA ↔ UA-CH parity** — User-Agent claims your real installed browser version; `sec-ch-ua*` headers, `navigator.userAgentData` high-entropy hints, and `navigator.platform` all agree (no more cross-API bot signals)
- WebGL vendor/renderer spoofed to match the profile's GPU (Windows D3D11 / macOS Metal / Linux OpenGL strings) — no more corrupted renderer strings
- Screen size, `devicePixelRatio`, `hardwareConcurrency`, `deviceMemory`, `navigator.webdriver` overridden per profile
- **`--transport obfs4`** — Tor over obfs4 bridges: ISP/DPI sees random bytes, not Tor. First use fetches bridges from torproject.org (captcha shown once, bridges cached in `~/.config/gray_net/bridges.txt`)

### v1.2.0
- `gn go --detach` — session loop in the background; `gn new` / `gn status` / `gn off` work live from any terminal (no Ctrl+C needed)
- `gn new` on a running loop rotates it in place (SIGUSR1) instead of opening a competing session
- Live progress: spinner on every connect phase (tor start, NEWNYM, exit-pin wait, page load) + waits until the session is really up before returning
- Demo video, Prohibited uses, and Security & privacy sections added to this README
- `gn verify` retries the exit-ip check instead of failing on a slow first circuit

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
- **Fingerprinting**: font-consistency models, Firefox profile hardening, audio-context noise
- **Ops**: better status views, JSON output mode, systemd units

Workflow: fork → feature branch → PR. Keep the core dependency-light (stdlib + playwright); no app-specific logic in core.

## License

[GPL-3.0](LICENSE) — free to use, modify, and redistribute under the same license.

## Disclaimer

Use Gray Net only against systems you are authorized to test. You are responsible for complying with applicable laws and each target's terms of service.

## Responsible Use Policy

Gray Net is developed for authorized penetration testing, security research, privacy testing, and defensive security education.

This tool must only be used on systems, websites, and infrastructure that you own or have explicit permission to test.

### Permitted Use

Users may use Gray Net to:

- Test security controls on systems they own or are authorized to assess.
- Evaluate browser session isolation, cookie handling, and fingerprinting behavior.
- Conduct authorized privacy and proxy connectivity tests.
- Research defensive security mechanisms in controlled environments.
- Identify weaknesses and improve website security.

### Prohibited Activities

Users must not use Gray Net to:

- Bypass website security controls, anti-abuse mechanisms, rate limits, or fraud-prevention systems without explicit authorization.
- Evade bans, access restrictions, or account limitations on third-party services.
- Automate spam, harassment, fraud, credential attacks, or other abusive activities.
- Access, disrupt, damage, or interfere with systems without authorization.
- Conceal malicious activity or facilitate illegal actions.
- Violate applicable laws, service agreements, or the rights of others.

### User Responsibility

Users are solely responsible for how they use, configure, and modify Gray Net. Having access to this tool does not grant permission to test any website or system.

Always obtain authorization, define the scope of testing, follow applicable laws, and respect the security controls of the target system.

### Security and Ethical Commitment

Gray Net is intended to support responsible security research and defensive testing. Misuse is contrary to the project's intended purpose.

If you discover a security vulnerability, report it responsibly to the affected system owner rather than exploiting it.

**Use Gray Net responsibly. Test with permission. Protect others. Improve security.**

