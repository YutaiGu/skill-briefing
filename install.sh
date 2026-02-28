#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/YutaiGu/skill-briefing.git}"
INSTALL_DIR="${INSTALL_DIR:-$PWD/skill-briefing}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$INSTALL_DIR/.venv"

log() {
  printf "[briefing-install] %s\n" "$1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1
}

ffmpeg_already_installed() {
  require_cmd ffmpeg
}

install_deps_linux() {
  local ffmpeg_needed=1
  if ffmpeg_already_installed; then
    ffmpeg_needed=0
    log "Detected existing ffmpeg, skip ffmpeg package install"
  fi

  if require_cmd apt-get; then
    sudo apt-get update
    if [ "$ffmpeg_needed" -eq 1 ]; then
      sudo apt-get install -y git curl python3 python3-venv ffmpeg
    else
      sudo apt-get install -y git curl python3 python3-venv
    fi
    return
  fi

  if require_cmd dnf; then
    if [ "$ffmpeg_needed" -eq 1 ]; then
      sudo dnf install -y git curl python3 python3-virtualenv ffmpeg
    else
      sudo dnf install -y git curl python3 python3-virtualenv
    fi
    return
  fi

  if require_cmd yum; then
    if [ "$ffmpeg_needed" -eq 1 ]; then
      sudo yum install -y git curl python3 ffmpeg
    else
      sudo yum install -y git curl python3
    fi
    return
  fi

  echo "Unsupported Linux package manager. Install manually: git curl python3 python3-venv ffmpeg"
  exit 1
}

install_deps_macos() {
  if ! require_cmd brew; then
    echo "Homebrew is required on macOS. Install from https://brew.sh first."
    exit 1
  fi

  brew update
  if ffmpeg_already_installed; then
    log "Detected existing ffmpeg, skip ffmpeg package install"
    brew install git python
  else
    brew install git python ffmpeg
  fi
}

install_deps() {
  os="$(uname -s)"
  case "$os" in
    Linux*) install_deps_linux ;;
    Darwin*) install_deps_macos ;;
    *)
      echo "Unsupported OS: $os"
      exit 1
      ;;
  esac
}

sync_repo() {
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [ -d "$INSTALL_DIR/.git" ]; then
    log "Updating existing repo in $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull
  else
    if [ -e "$INSTALL_DIR" ] && [ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null || true)" ]; then
      echo "INSTALL_DIR exists and is not a git repo: $INSTALL_DIR"
      echo "Use an empty directory or pass INSTALL_DIR=/path/to/dir"
      exit 1
    fi
    log "Cloning repo to $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
  fi
}

setup_python_env() {
  log "Creating virtual environment"
  python3 -m venv "$VENV_DIR"

  log "Installing Python dependencies"
  "$VENV_DIR/bin/pip" install -U pip setuptools wheel
  "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
}

install_launcher() {
  mkdir -p "$BIN_DIR"
  cat > "$BIN_DIR/briefing" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/main.py" "\$@"
EOF
  chmod +x "$BIN_DIR/briefing"
}

print_done() {
  log "Installed successfully."
  if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
    echo
    echo "Add this to your shell profile:"
    echo "export PATH=\"$BIN_DIR:\$PATH\""
  fi
  echo
  echo "Run: briefing"
}

main() {
  install_deps
  sync_repo
  setup_python_env
  install_launcher
  print_done
}

main "$@"
