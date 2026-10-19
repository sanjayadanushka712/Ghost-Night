#!/usr/bin/env bash
set -e

echo "ghostnet installer"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
fi

if command -v pacman >/dev/null; then
  command -v tor >/dev/null || {
    echo ".. installing tor"
    $SUDO pacman -S --needed --noconfirm tor
  }
  command -v curl >/dev/null || $SUDO pacman -S --needed --noconfirm curl
else
  echo "!! no pacman found — install tor and curl manually"
fi

VENV="$HOME/.local/share/ghostnet/venv"
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

echo
echo "done. quick start:"
echo "  gn verify            # check tor works"
echo "  gn go https://site   # new IP + new device session"
echo "  gn new               # rotate now"
echo "  gn status / gn off"
