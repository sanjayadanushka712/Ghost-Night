#!/usr/bin/env bash
set -e

echo "ghost_night installer"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
fi

if command -v pacman >/dev/null; then
  command -v tor >/dev/null || $SUDO pacman -S --needed --noconfirm tor
  command -v curl >/dev/null || $SUDO pacman -S --needed --noconfirm curl
elif command -v apt-get >/dev/null; then
  $SUDO apt-get update -qq
  command -v tor >/dev/null || $SUDO apt-get install -y -qq tor
  command -v curl >/dev/null || $SUDO apt-get install -y -qq curl
elif command -v dnf >/dev/null; then
  command -v tor >/dev/null || $SUDO dnf install -y tor
  command -v curl >/dev/null || $SUDO dnf install -y curl
else
  echo "!! unknown package manager — install tor and curl manually"
fi

VENV="$HOME/.local/share/ghost_night/venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo ".. creating venv"
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -c "import playwright" 2>/dev/null || {
  echo ".. installing playwright"
  "$VENV/bin/pip" install --quiet playwright
}

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
ln -sf "$(pwd)/gn" "$BIN_DIR/gn"
echo ".. linked $BIN_DIR/gn"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "!! add to PATH:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

if ! command -v google-chrome-stable >/dev/null && ! command -v google-chrome >/dev/null \
   && ! command -v chromium >/dev/null && ! command -v chromium-browser >/dev/null \
   && ! command -v firefox >/dev/null; then
  echo "!! no browser found — install google-chrome, chromium, or firefox"
fi

echo
echo "done. quick start:"
echo "  gn verify            # check tor works"
echo "  gn go https://site   # fresh device session on a target"
echo "  gn new               # continue as a brand-new user"
echo "  gn status / gn off"
