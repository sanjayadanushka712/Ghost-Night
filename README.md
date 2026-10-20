# Ghost Night

<p align="center"><img src="assets/GhostNight.png" width="180" alt="Ghost Night logo"></p>

<p align="center">
  <b>Browser Fingerprint &amp; Identity Rotation Toolkit</b><br>
  fresh IP · fresh browser fingerprint · fresh session — on demand
</p>

<p align="center">
  <img alt="version" src="https://img.shields.io/badge/version-1.3.0-46d746">
  <img alt="license" src="https://img.shields.io/badge/license-GPL--3.0-46d746">
  <img alt="platform" src="https://img.shields.io/badge/platform-Linux-lightgrey">
  <img alt="tor" src="https://img.shields.io/badge/transport-Tor%20%7C%20obfs4%20%7C%20proxy%20%7C%20direct-46d746">
</p>

---

**Ghost Night** is a **Browser Fingerprint & Identity Rotation Toolkit** for authorized security testing. It turns one machine into many "devices" for testing how web applications track, rate-limit, and ban users — each session gets a fresh coherent browser profile and, optionally, a fresh public IP via Tor, obfs4, or your own proxy. When a session hits a limit, `gn new` continues as a brand-new user on the same site.

Built for **authorized pentesting**: rate-limit checks, trial/expiry controls, device- and IP-ban enforcement, anti-abuse logic.

<img width="606" height="295" alt="image" src="https://github.com/user-attachments/assets/d85010bd-1176-45dc-9e67-8c88f912d2b3" />

## Demo

🎥 **Watch the walkthrough:** [Ghost Night demo video](https://drive.google.com/file/d/1VMZLD7_RlxjPKBVr9buRfhU_ZmayETO7/view?usp=sharing)

## What it defeats

| Signal apps use to track "you" | Ghost Night countermeasure |
|---|---|
| Cookies / localStorage device IDs | brand-new browser profile every rotation — zero storage carryover |
| Public IP address | Tor circuit rotation (`NEWNYM`) or your own rotating proxy |
| WebRTC / DNS leaking the real IP | WebRTC policy locked off, DNS forced through the proxy |
| UA / locale / viewport / timezone | **coherent device profile** — one plausible machine (OS, screen, dpr, cores, GPU, tz+locale all match), browser version = your real installed version (UA ↔ UA-CH can't disagree) |
| Canvas / WebGL fingerprint | deterministic-per-session canvas noise + WebGL vendor/renderer spoofed to match the profile's GPU |
| Font list | masked to the profile OS — host-only fonts measure as absent |
| Automation tells (`navigator.webdriver`, plugin types, `window.chrome`) | fully patched — passes bot.sannysoft.com 56/56 |
| Cross-API contradictions (the #1 bot signal) | `navigator.platform`, `userAgentData`, screen size, `devicePixelRatio`, `hardwareConcurrency`, `deviceMemory` all overridden to the same profile |
| Cross-layer geo contradiction (IP vs timezone) | when Tor/obfs4 or a country-tagged proxy is used, the exit's country drives the profile's timezone **and** locale (exit in Germany → `Europe/Berlin`/`de-DE`) |
| Chrome-only fingerprint surface (Blink vs Gecko tells) | `--firefox` runs a **real Firefox identity** — Firefox UA (`rv:<major>.0`), matching platform/cores/tz/locale, Firefox-hardening `user_prefs`; passes bot.sannysoft.com 55/56 |
| Datacenter-IP reputation (Tor exits are flagged) | `--proxy-pool` rotates through your own residential/mobile proxies — one fresh IP per session |
| Bot-like input (instant clicks, teleport mouse, paste) | `--human` mode (bowed arcs, per-key typing jitter) and `--behavioral` — a real motor/reading model: Fitts-law targeting, ballistic overshoot, scroll momentum, content-density dwell, idle drift |

**TLS fingerprint (JA3/JA4) — mostly a non-issue here.** Ghost Night drives your *real* Chromium/Firefox binaries, and Tor/SOCKS proxies are opaque (they don't terminate TLS), so the browser's authentic ClientHello reaches the server untouched. Verified against `tls.peet.ws`: Chrome sends a real Chrome JA3/JA4 both direct and through Tor SOCKS; `--firefox` sends a genuine Firefox JA3. The only case where JA3 diverges is an **`http://` (TLS-terminating) proxy**, which re-originates TLS with a non-browser stack — prefer `socks5://` proxies in `--proxy-pool` to avoid it.

**What we can and can't do — honestly.** Each remaining hard signal, and where Ghost Night stands:

| hard signal | what Ghost Night does | verdict |
|---|---|---|
| Account-tied limits (quota follows the login, not the device) | rotates the whole device+IP identity, so free/trial-style limits reset — but a paid/authenticated account's quota is server-side and can't be reset | **partly** (trial/anon limits yes, account quotas no) |
| Datacenter-IP reputation (Tor exits flagged) | `--proxy-pool` with your own residential/mobile proxies; `--transport obfs4` hides Tor from ISP DPI | **yes** (with your own clean IPs) |
| Keystroke/typing cadence | `--human` adds realistic per-key inter-key timing; `--behavioral` models mouse/scroll/reading | **partly** (covers input *rhythm*, not full typing biomechanics — no clean-room key-dynamics model) |
| CAPTCHAs served to suspicious IPs | cleaner exit/proxy selection raises the reputation bar | **mitigated** (not solved — a challenge still needs a real solve) |
| Cross-API + IP-geo contradictions (the #1 script signal) | coherent device profiles + cross-layer geo coherence: every API, and the IP geography, tell one story | **yes** |
| Fingerprint scripts (FingerprintJS open-source / device-fingerprint JS) | coherent profiles pass these — every value agrees | **yes** |
| FingerprintJS Pro-class, server-side ML, hardware-bound | no honest browser-side tool beats server-side ML + account correlation | **no** (and no tool claiming otherwise is being straight with you) |

MAC-address rotation is intentionally out of scope — MAC is Layer-2 and never reaches internet servers.

**Raw HTTP mode (`gn fetch`) — what it is and isn't.** It carries a coherent identity at the *network* layer (TLS JA3/JA4, HTTP/2 fingerprint, header order, User-Agent) via real browser impersonation, with the UA version derived from the TLS fingerprint so they can't disagree. What it **is not**: a browser. There is no JS engine, so it announces **no** `navigator`/canvas/WebGL surface at all — on script-dependent or fingerprint-script sites that absence is itself a signal. Use it for APIs, feed/metadata fetches, and header/TLS-level checks; use the browser path when a site runs JS.

## Security & privacy

- **Local-only** — Ghost Night has no server, no telemetry, no phone-home. Everything (state, logs, profiles) stays in `~/.config/ghost_night/` and `~/.local/share/ghost_night/`.
- **Profiles are deleted on rotation** — each browser profile (cookies, storage) is wiped when the next identity starts; use `--keep-profiles` only if you need forensic artifacts.
- **Evidence log may contain sensitive data** — `log.jsonl` records IPs, fingerprints, and timestamps of your sessions. Treat it like test evidence: don't share it publicly, delete it when the engagement ends (`gn off` clears state, remove the log manually if needed).
- **Tor exit nodes can read unencrypted traffic** — never send passwords, tokens, or personal data over plain `http://` through Tor. HTTPS is encrypted end-to-end even via exits.
- **Ghost Night does not anonymize YOU against the network operator** — your ISP/employer can see you're using Tor; Tor traffic itself is visible (though content is encrypted). Use `--transport obfs4` to make Tor traffic indistinguishable from random encrypted bytes on the wire (ISP DPI can't tell it's Tor). For full anonymity against the network operator use a VPN/Tails — not this tool.
- **Fingerprint spoofing is best-effort** — coherent profiles defeat casual cross-session tracking and fingerprint scripts; a motivated adversary with server-side signals (FingerprintJS Pro-class) is still a stronger opponent.

## Dependencies

| package | why | needed for |
|---|---|---|
| `tor` | IP rotation — new exit circuit per session (`NEWNYM`) | `--transport tor` (default) |
| `obfs4proxy` (optional) | pluggable transport — Tor traffic disguised as random bytes, so your ISP can't see you're using Tor | `--transport obfs4` |
| `python3` (≥3.10) | runs Ghost Night | everything |
| `curl` | checks real IP vs Tor exit IP | `gn verify`, exit-IP checks |
| Chrome or Chromium | the browser each session runs in (Firefox via `--firefox`) | sessions |
| `python-playwright` | drives the browser, injects per-session fingerprint | sessions — **installed automatically** into a private venv by `install.sh` |
| `python-curl_cffi` (optional) | raw HTTP mode — real browser TLS/HTTP2 (JA3/JA4) impersonation, no browser | `gn fetch`, `gn probe` — installed automatically by `install.sh` |

Only **`tor` and `curl`** must be installed manually. Playwright and curl_cffi are fetched into `~/.local/share/ghost_night/venv` by the installer — no system Python changes.

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
python3 -m venv ~/.local/share/ghost_night/venv
~/.local/share/ghost_night/venv/bin/pip install playwright curl_cffi
python -m playwright install firefox   # optional — only for `--firefox`
ln -sf "$PWD/gn" ~/.local/bin/gn     # then ensure ~/.local/bin is in PATH
```

### Other requirements

- **A browser must be installed** — Ghost Night uses your system Chrome/Chromium (default) or Firefox (`--firefox`); the installer warns if none is found. Raw HTTP mode (`gn fetch`) needs no browser.
- **`~/.local/bin` in PATH** — so the `gn` command resolves; installer prints the exact line if needed:
  `export PATH="$HOME/.local/bin:$PATH"` (add to `~/.bashrc` or `~/.zshrc`)
- **A desktop session** — headed (visible) browser windows need a display (X11/Wayland); `--headless` works without one.
- **Free local ports 19050/19051** — Tor's SOCKS and control ports (changed in `ghost_night/tor.py` if they clash).
- **Internet access** — to bootstrap Tor and load target sites; `install.sh` also downloads Playwright and curl_cffi into the venv.

## Install

```bash
git clone https://github.com/Sanjaya-Danushka/Ghost-Night.git
cd Ghost-Night
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
gn doctor                       # diagnose env: deps, browsers, bridges, venv
gn test                         # self-check: launch each engine/transport and score fingerprinting
gn fetch URL                    # raw HTTP request (no browser) with a coherent TLS/UA identity
gn probe                        # show the JA3/JA4 + HTTP2 fingerprint a server sees
gn off                          # stop everything, clean up
```

`status`, `verify`, `doctor`, and `test` accept `--json` for scripting.

## Per-site behavior

Every app signals "you're out" differently — pick the mode that fits:

| site behavior | command |
|---|---|
| common limit text ("limit reached", "no credits", "upgrade to continue", ...) | `gn go URL` — generic watcher, stops itself |
| custom wording / modal / redirect | `gn go URL --detect "its wording"` — auto-rotates on match |
| silent block, no message | `gn go URL --no-watch` — plain sessions, rotate manually with `gn new` |
| timer-based trial | `gn go URL --every 25m` — rotate on a clock, before expiry |

Sites that block Tor datacenter IPs (Cloudflare-class) are handled by a built-in exit-strategy ladder — no VPN needed:

1. **proven exits** — exits that previously got HTTP 200 on this site are remembered (`~/.config/ghost_night/good_exits.json`) and pinned via `ExitNodes`
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
gn go URL --transport proxy --proxy-pool proxies.txt   # rotate through a file of proxies
gn go URL --detect "regex"                   # custom limit pattern (auto-rotate on match)
gn go URL --no-watch                         # no limit watching at all
gn go URL --every 25m                        # timed rotation
gn go URL --once                             # single session
gn go URL --detach                           # background loop; control with gn new/status/off
gn go URL --human                            # human-like mouse/scroll activity on load
gn go URL --human deep --human-minutes 5     # full behavioral engine: Fitts targeting, scroll momentum, reading dwell, idle drift
gn go URL --behavioral                       # alias for --human deep
gn go URL --firefox                          # real Firefox identity (not Chrome in disguise)
gn go URL --firefox --headless --keep-profiles
gn new --target https://other-site.com       # switch sites
gn fetch https://api.example.com --json      # raw request, no browser; coherent TLS/UA
gn fetch URL --transport tor -X POST --json-body '{"a":1}' -H 'X-Api-Key: ...'
gn fetch URL --firefox --cookie-jar ~/.config/ghost_night/cj.txt   # persist cookies + identity across calls
gn probe --json                              # what JA3/JA4/UA the server sees for a raw request
gn status --json                             # machine-readable state (also verify/doctor/test)
gn test --transport tor,obfs4,direct         # self-check fingerprinting across engines/transports
```

## How a rotation works

1. Tor gets `NEWNYM` → next connection uses a new exit circuit (new public IP); blocked exits are retried automatically.
2. Old browser profile is closed and deleted.
3. A new profile is created with a fresh identity: one coherent device profile (OS + screen + dpr + GPU + cores + tz + locale all from the same plausible machine), real browser version, fresh canvas noise seed. Under Tor/obfs4 the exit IP's country is looked up first, so the profile's timezone + locale match the IP's geography.
4. The browser launches through the proxy and opens the target.
5. The event is logged (`~/.local/share/ghost_night/log.jsonl`) — evidence for your pentest report.

## Files

- `~/.config/ghost_night/` — tor config, control cookie, logs, proven-exit cache (`good_exits.json`), obfs4 bridges (`bridges.txt`), proxy pool (`proxies.txt` — default location if you omit `--proxy-pool`; optional `cc=XX` country tag per line)
- `~/.local/share/ghost_night/sessions/` — live browser profiles (deleted on rotate)
- `~/.local/share/ghost_night/log.jsonl` — rotation history (IP, fingerprint, timestamp)

## Changelog

### v1.3.0
- **Coherent device profiles** — every session picks one plausible machine (OS, screen, dpr, viewport, GPU, cores, memory, timezone+locale pairs) instead of mixing random values that contradict each other
- **UA ↔ UA-CH parity** — User-Agent claims your real installed browser version; `sec-ch-ua*` headers, `navigator.userAgentData` high-entropy hints, and `navigator.platform` all agree (no more cross-API bot signals)
- WebGL vendor/renderer spoofed to match the profile's GPU (Windows D3D11 / macOS Metal / Linux OpenGL strings) — no more corrupted renderer strings
- Screen size, `devicePixelRatio`, `hardwareConcurrency`, `deviceMemory` overridden per profile
- **Automation-leak hardening** — `navigator.plugins`/`mimeTypes` are real `PluginArray`/`MimeTypeArray` with `[object Plugin]`/`[object MimeType]` tags; `navigator.webdriver` fully removed; `window.chrome.runtime` shim, `notifications` permission, `pdfViewerEnabled`, and `navigator.languages` all filled in. **Verified 0/56 failures on bot.sannysoft.com**
- **OS-matched font masking** — fonts the profile OS shouldn't have (e.g. Linux's Noto on a Windows profile) are made to measure as *absent* via a document-start `@font-face` mask; no more "Windows UI but Linux fonts" tell
- **`--human` mode** — bowed cubic-bezier mouse movement (not teleport), natural clicks, and per-character key events with jitter
- WebGPU adapter vendor/architecture spoofed to match the profile's GPU; deterministic audio-context fingerprint noise
- **`--transport obfs4`** — Tor over obfs4 bridges: ISP/DPI sees random bytes, not Tor. First use fetches bridges from torproject.org (captcha shown once, bridges cached in `~/.config/ghost_night/bridges.txt`)
- **Coherent Firefox profiles** — `--firefox` now runs a real Firefox identity, not a Chrome body with a Firefox UA: Firefox-formatted UA drawn from the installed binary, matching platform/cores/timezone/locale/WebGL, and Firefox privacy-hardening `user_prefs` (telemetry/webdriver/beacon off). The `navigator` surface is now **engine-aware** too — no `window.chrome` shim, empty `navigator.vendor`, no `deviceMemory`, and a real `PDF.js` plugin in a native `PluginArray` — so a Firefox session doesn't leak Chrome-only tells. Fails only the `Chrome (New)` probe, which a genuine Firefox *should* fail
- **Proxy-pool rotation** — `--transport proxy --proxy-pool proxies.txt` picks a fresh proxy from a file (one URL per line, `#` comments allowed) on every session *and* every rotation; the pool is remembered so `gn new` keeps rotating through it. Tag a line with a country (`socks5://host:1080 cc=DE` or `socks5://host:1080|DE`) and the profile's timezone+locale are matched to it
- **Cross-layer geo coherence** — when using Tor/obfs4, Ghost Night looks up the exit IP's country and picks a device profile whose timezone+locale fit it, so a Germany exit no longer pairs with an `America/New_York` profile (no IP-geo ↔ timezone contradiction)
- **`gn doctor`** — one-shot environment diagnosis (tor, obfs4proxy, bridges, browsers, curl, venv, config/data dirs), so you know what's missing before a test
- **`gn test`** — self-check that launches each engine × transport and scores fingerprinting on bot.sannysoft.com, printing a pass/fail report
- **Behavioral engine** (`--human deep` / `--behavioral`) — models motor control and reading instead of flat randomness: Fitts's-law targeting (move time scales with distance ÷ target size), ballistic overshoot + micro-correction, scroll momentum (accelerate → cruise → decelerate), reading dwell proportional to content density, occasional clicks on real elements, and idle micro-drift — all paced with slight fatigue over the session
- **`--json` mode** — `status`, `verify`, `doctor`, and `test` emit machine-readable JSON for scripting/CI
- **Raw HTTP mode** — `gn fetch URL` sends requests **with no browser at all**, carrying a coherent identity at the network layer: the TLS ClientHello (JA3/JA4), HTTP/2 settings, header order, and User-Agent all describe one real browser on one machine. TLS-first design (curl_cffi impersonation picks the fingerprint, then OS/locale/tz/UA are derived to match), so the UA never disagrees with the JA3. Routes through `--transport tor/obfs4/proxy/direct`, supports `-X`, `-H`, `-d`, `--json-body`, `--json`, and `--cookie-jar` (which also pins the identity so cookies *and* browser stay stable across calls). `gn probe` shows the JA3/JA4 + HTTP2 fingerprint a server actually sees. **Honest scope:** this shapes only what the server sees at L7/TLS — it announces no JS `navigator` surface at all (there is no JS engine), which is itself a signal on script-dependent sites; use the browser path for those.
- Renamed project to **Ghost Night** (was ghostnet)

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
- **Fingerprinting**: font-consistency models, audio-context noise tuning, WebGPU/WebGL2 surfaces
- **Transports**: uTLS/JA3-client spoofing for TLS-terminating (`http://`) proxies, proxy health-check/geo-tagging tools
- **Ops**: better status views, JSON output mode, systemd units

Workflow: fork → feature branch → PR. Keep the core dependency-light (stdlib + playwright); no app-specific logic in core.

## License

[GPL-3.0](LICENSE) — free to use, modify, and redistribute under the same license.

## Disclaimer

Use Ghost Night only against systems you are authorized to test. You are responsible for complying with applicable laws and each target's terms of service.

## Responsible Use Policy

Ghost Night is developed for authorized penetration testing, security research, privacy testing, and defensive security education.

This tool must only be used on systems, websites, and infrastructure that you own or have explicit permission to test.

### Permitted Use

Users may use Ghost Night to:

- Test security controls on systems they own or are authorized to assess.
- Evaluate browser session isolation, cookie handling, and fingerprinting behavior.
- Conduct authorized privacy and proxy connectivity tests.
- Research defensive security mechanisms in controlled environments.
- Identify weaknesses and improve website security.

### Prohibited Activities

Users must not use Ghost Night to:

- Bypass website security controls, anti-abuse mechanisms, rate limits, or fraud-prevention systems without explicit authorization.
- Evade bans, access restrictions, or account limitations on third-party services.
- Automate spam, harassment, fraud, credential attacks, or other abusive activities.
- Access, disrupt, damage, or interfere with systems without authorization.
- Conceal malicious activity or facilitate illegal actions.
- Violate applicable laws, service agreements, or the rights of others.

### User Responsibility

Users are solely responsible for how they use, configure, and modify Ghost Night. Having access to this tool does not grant permission to test any website or system.

Always obtain authorization, define the scope of testing, follow applicable laws, and respect the security controls of the target system.

### Security and Ethical Commitment

Ghost Night is intended to support responsible security research and defensive testing. Misuse is contrary to the project's intended purpose.

If you discover a security vulnerability, report it responsibly to the affected system owner rather than exploiting it.

**Use Ghost Night responsibly. Test with permission. Protect others. Improve security.**

