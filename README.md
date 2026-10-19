# ghostnet

**Anonymous device rotation for the internet — new IP, new browser fingerprint, fresh session on demand.**

`ghostnet` (`gn`) makes your machine appear as a brand-new device to any web app: it rotates your public IP through Tor and launches each session in a completely fresh, fingerprint-randomized browser context. When a session hits a limit or gets flagged, a new identity takes its place in seconds — no manual cookie clearing, no VPN juggling.

## What it does

| Signal the app tracks | ghostnet countermeasure |
|---|---|
| Cookies / localStorage device ID | brand-new browser profile every rotation (zero storage carryover) |
| IP address | Tor circuit rotation (`NEWNYM`) per session |
| WebRTC / DNS leaks | WebRTC policy locked off, DNS forced through the proxy |
| UA / locale / viewport / timezone | randomized per session |
| Canvas / WebGL fingerprint | deterministic-per-session noise (seeded) |

## Install

```bash
git clone https://github.com/Sanjaya-Danushka/ghostnet.git
cd ghostnet
./install.sh
```

Requires: Linux, `tor`, `python-playwright` (uses your installed Chrome), `curl`. No root needed at runtime.

## Quick start

```bash
gn verify                      # check tor works (real ip vs tor exit ip)
gn go https://example.com      # start: new IP + new device session
gn new                         # rotate right now (new IP + new device)
gn status                      # tor, current session, recent events
gn off                         # kill everything, clean up profiles
```

### Auto-rotation modes

```bash
gn go https://site.com --every 25m            # rotate on a timer
gn go https://site.com --detect "no tokens|limit reached|expired"   # rotate when the page says so
gn go https://site.com --every 25m --detect "limit" --headless      # both, headless
```

### Other options

```bash
gn go https://site --once              # single session, no loop
gn go https://site --transport proxy --proxy socks5://127.0.0.1:1080   # use your own proxy instead of tor
gn go https://site --transport direct  # no proxy at all (testing)
gn go https://site --firefox           # Firefox channel instead of Chrome
gn go https://site --keep-profiles     # keep profiles on disk after rotate
```

## How a rotation works

1. Tor gets `NEWNYM` → next connection uses a new exit circuit (new public IP).
2. Old browser profile is closed and deleted.
3. A new profile directory is created with a fresh identity: new UA/platform, viewport, timezone, locale, canvas/WebGL noise seed.
4. Browser launches through the proxy, target URL opens.
5. Event is logged (JSONL, `~/.local/share/ghostnet/log.jsonl`).

## Threat model — read this

**Defeats:** IP-based limits, cookie/storage device IDs, WebRTC/DNS leaks, naive browser fingerprinting (UA, screen, timezone, canvas/webgl noise).

**Does not defeat:** commercial hardware-bound fingerprinting (FingerprintJS Pro-class) at high confidence, account-tied limits (login-based), TLS/JA3 correlation across all sessions from one machine.

MAC address rotation is not included: MAC is a local-network (Layer-2) identifier and never reaches internet servers.

## Commands

| command | meaning |
|---|---|
| `gn go <url>` | start — auto session loop on target |
| `gn new` | rotate right now |
| `gn status` | show state |
| `gn verify` | check tor + exit ip |
| `gn off` | stop everything, clean up |

## Files

- `~/.config/ghostnet/` — tor config, control cookie, logs
- `~/.local/share/ghostnet/sessions/` — live browser profiles (deleted on rotate)
- `~/.local/share/ghostnet/log.jsonl` — rotation history for reports

## License

MIT
