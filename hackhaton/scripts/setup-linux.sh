#!/usr/bin/env bash
# VayOBD — New Developer Setup (Linux)
# Run from the repo root: bash scripts/setup-linux.sh
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

step() { echo -e "\n${BLUE}${BOLD}▶ $1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTORY_PATH="$HOME/.cache/vayobd/ree-vehicle-configs"

echo -e "${GREEN}${BOLD}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║    VayOBD — New Developer Setup (Linux)    ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"
echo "  Steps: Twingate → Tools → SSH key → Inventory → Dependencies → Config"
echo ""
read -rp "  Press Enter to begin..."

# ─── Detect package manager ─────────────────────────────────────────────────
if   command -v apt-get &>/dev/null; then PKG_MGR="apt"
elif command -v dnf     &>/dev/null; then PKG_MGR="dnf"
elif command -v yum     &>/dev/null; then PKG_MGR="yum"
elif command -v pacman  &>/dev/null; then PKG_MGR="pacman"
else echo "Unsupported Linux distro. Install Python 3.11, Node 20, Git manually then re-run."; exit 1
fi
ok "Detected package manager: $PKG_MGR"

install_pkg() {
    case "$PKG_MGR" in
        apt)    sudo apt-get install -y "$@" ;;
        dnf)    sudo dnf install -y "$@" ;;
        yum)    sudo yum install -y "$@" ;;
        pacman) sudo pacman -S --noconfirm "$@" ;;
    esac
}

# ─── Step 1: Twingate ───────────────────────────────────────────────────────
step "Step 1/6 — Twingate (fleet network access)"
echo "  Twingate gives you access to the Vay fleet network."
echo "  Without it, checks against live vehicles/telestations will fail."
echo ""
echo "  Install the Twingate client for Linux: https://www.twingate.com/download"
echo ""
echo "  After installing:"
echo "    1. Sign in with your @vay.io Google account"
echo "    2. Connect to the 'Vay Fleet' resource"
echo "       (Ask your team lead for the resource name if unsure)"
echo ""
read -rp "  Press Enter once Twingate is installed and connected (or Enter to skip for fixture/demo mode)..."

# ─── Step 2: System tools ───────────────────────────────────────────────────
step "Step 2/6 — System tools (Python 3.11, Node 20, Git)"

if ! command -v git &>/dev/null; then
    install_pkg git && ok "Git installed"
else
    ok "Git already installed"
fi

if ! command -v python3 &>/dev/null || ! python3 -c "import sys; assert sys.version_info >= (3,11)" 2>/dev/null; then
    echo "  Installing Python 3.11..."
    case "$PKG_MGR" in
        apt)
            sudo apt-get update -qq
            if apt-cache show python3.11 &>/dev/null; then
                install_pkg python3.11 python3.11-venv python3.11-dev
            else
                sudo apt-get install -y software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt-get update -qq
                install_pkg python3.11 python3.11-venv python3.11-dev
            fi
            sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 || true
            ;;
        dnf|yum) install_pkg python3.11 python3.11-pip ;;
        pacman)  install_pkg python ;;
    esac
    ok "Python 3.11 installed"
else
    ok "Python $(python3 --version) already installed"
fi

if ! command -v node &>/dev/null; then
    echo "  Installing Node 20..."
    case "$PKG_MGR" in
        apt)
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            install_pkg nodejs
            ;;
        dnf|yum)
            curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
            install_pkg nodejs
            ;;
        pacman) install_pkg nodejs npm ;;
    esac
    ok "Node $(node --version) installed"
else
    ok "Node $(node --version) already installed"
fi

# ─── Step 3: SSH key ────────────────────────────────────────────────────────
step "Step 3/6 — SSH key setup"

SSH_KEY="$HOME/.ssh/id_ed25519"
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"

if [[ ! -f "$SSH_KEY" ]]; then
    echo "  No SSH key found — generating a new one."
    read -rp "  Enter your Vay email address: " VAY_EMAIL
    ssh-keygen -t ed25519 -C "$VAY_EMAIL" -f "$SSH_KEY" -N ""
    ok "SSH key generated at $SSH_KEY"
else
    ok "SSH key already exists at $SSH_KEY"
fi

eval "$(ssh-agent -s)" > /dev/null
ssh-add "$SSH_KEY" 2>/dev/null || true

echo ""
echo -e "  ${BOLD}Your public key (copy this):${NC}"
echo "  ┌──────────────────────────────────────────────────────────────┐"
sed 's/^/  │ /' "${SSH_KEY}.pub"
echo "  └──────────────────────────────────────────────────────────────┘"
echo ""
echo "  Add it to GitHub: https://github.com/settings/ssh/new"
echo ""
read -rp "  Press Enter once you've added the key to GitHub..."

echo "  Testing GitHub SSH connection..."
if ssh -o StrictHostKeyChecking=no -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    ok "GitHub SSH connection verified"
else
    warn "Could not verify GitHub connection — continuing anyway."
fi

# ─── Step 4: Vehicle inventory ──────────────────────────────────────────────
step "Step 4/6 — Vehicle inventory (ree-vehicle-configs)"

mkdir -p "$HOME/.cache/vayobd"
if [[ -d "$INVENTORY_PATH/.git" ]]; then
    ok "Inventory already cloned — pulling latest..."
    git -C "$INVENTORY_PATH" pull --ff-only || warn "Could not pull (continuing with cached version)"
else
    echo "  Cloning ree-vehicle-configs..."
    if git clone git@github.com:Reemote/ree-vehicle-configs.git "$INVENTORY_PATH"; then
        ok "Inventory cloned"
    else
        warn "Could not clone ree-vehicle-configs (no GitHub access yet?)."
        warn "Re-run this script after your GitHub access is granted."
    fi
fi

# ─── Step 5: Backend + frontend dependencies ────────────────────────────────
step "Step 5/6 — Backend (Python) and frontend (Node) dependencies"

cd "$REPO_ROOT"
[[ ! -d ".venv" ]] && python3 -m venv .venv
source .venv/bin/activate
pip install -e backend --quiet
ok "Backend installed"

cd "$REPO_ROOT/frontend"
npm install --silent
ok "Frontend dependencies installed"

# ─── Step 6: .env + launchers ───────────────────────────────────────────────
step "Step 6/6 — Configuration and run scripts"

cd "$REPO_ROOT"

echo "  Fleet SSH credentials are needed to run checks against real hosts."
echo "  Request them via the Vay IT Service Desk:"
echo "    → https://vayio.atlassian.net/servicedesk/customer/portals"
echo ""
read -rp "  Path to fleet SSH private key   (Enter to skip — uses fixture mode): " FLEET_KEY
read -rp "  Path to fleet known_hosts file  (Enter to skip — uses fixture mode): " FLEET_HOSTS

if [[ -n "$FLEET_KEY" && -n "$FLEET_HOSTS" ]]; then
    EXECUTOR="ssh"
else
    EXECUTOR="fixture"
fi

cat > .env << EOF
# VayOBD runtime configuration — generated by scripts/setup-linux.sh
# Edit any value here; changes take effect on next server restart.
# See .env.example for all available options.

VAYOBD_EXECUTOR=$EXECUTOR
VAYOBD_INVENTORY_PATH=$INVENTORY_PATH
${FLEET_KEY:+VAYOBD_SSH_KEY=$FLEET_KEY}
${FLEET_HOSTS:+VAYOBD_SSH_KNOWN_HOSTS=$FLEET_HOSTS}

# Uncomment when running in production (after npm run build in frontend/):
# VAYOBD_STATIC_DIR=./frontend/dist
EOF
ok "Created .env"

cat > run-dev.sh << 'DEVSCRIPT'
#!/usr/bin/env bash
# Start VayOBD in development mode (fixture executor, Vite on :5173, API on :8000)
# Usage: VAYOBD_DEV_USER=you@vay.io ./run-dev.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$REPO_ROOT/.venv/bin/activate"

DEV_USER="${VAYOBD_DEV_USER:-dev@local}"
echo "Starting VayOBD (dev) as $DEV_USER ..."

VAYOBD_EXECUTOR=fixture \
    uvicorn vayobd.app:app --reload --port 8000 &
BACKEND_PID=$!
echo "✓ Backend  → http://localhost:8000"

cd "$REPO_ROOT/frontend"
VAYOBD_DEV_USER="$DEV_USER" npm run dev &
FRONTEND_PID=$!
echo "✓ Frontend → http://localhost:5173"

echo ""
echo "Press Ctrl+C to stop both processes."
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT TERM
wait
DEVSCRIPT
chmod +x run-dev.sh
ok "Created run-dev.sh"

cat > run-prod.sh << 'PRODSCRIPT'
#!/usr/bin/env bash
# Start VayOBD in production mode (built SPA served by uvicorn on :8000)
# Requires .env to have VAYOBD_EXECUTOR=ssh + SSH credentials configured.
# Usage: ./run-prod.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$REPO_ROOT/.venv/bin/activate"

echo "Building frontend..."
cd "$REPO_ROOT/frontend"
npm run build
cd "$REPO_ROOT"
echo "✓ Frontend built → frontend/dist/"

export VAYOBD_STATIC_DIR="$REPO_ROOT/frontend/dist"

echo "Starting server..."
exec uvicorn vayobd.app:app --host 0.0.0.0 --port 8000
PRODSCRIPT
chmod +x run-prod.sh
ok "Created run-prod.sh"

# ─── Optional: nfpm for building the .deb (spec 006) ────────────────────────
# nfpm is used by ./packaging/build.sh to produce vayobd_*.deb. Not needed for
# day-to-day development; install it once if you are the platform engineer who
# cuts releases. Manual one-liner so the existing setup flow stays fast.
#
#   curl -sSfL -o /tmp/nfpm.deb \
#     https://github.com/goreleaser/nfpm/releases/latest/download/nfpm_amd64.deb \
#   && sudo dpkg -i /tmp/nfpm.deb && rm /tmp/nfpm.deb
#
# (Alternative without root: download the *.tar.gz from the same release and
# drop `nfpm` into ~/.local/bin/.)

# ─── Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ Setup complete!"
echo ""
echo "  Development (fixture mode, Vite hot-reload):"
echo "    VAYOBD_DEV_USER=you@vay.io ./run-dev.sh"
echo "    → http://localhost:5173"
echo ""
echo "  Production (built SPA, live SSH executor):"
echo "    ./run-prod.sh"
echo "    → http://localhost:8000"
echo ""
echo "  Settings: edit .env (see .env.example for all options)"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
