#!/usr/bin/env bash
# VayOBD — New Developer Setup (macOS)
# Run from the repo root: bash scripts/setup-mac.sh
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

step() { echo -e "\n${BLUE}${BOLD}▶ $1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTORY_PATH="$HOME/.cache/vayobd/ree-vehicle-configs"

echo -e "${GREEN}${BOLD}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║    VayOBD — New Developer Setup (macOS)    ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"
echo "  Steps: Twingate → Tools → SSH key → Inventory → Dependencies → Config"
echo ""
read -rp "  Press Enter to begin..."

# ─── Step 1: Twingate ───────────────────────────────────────────────────────
step "Step 1/6 — Twingate (fleet network access)"
echo "  Twingate gives you access to the Vay fleet network."
echo "  Without it, checks against live vehicles/telestations will fail."
echo ""
echo "  1. Download from: https://www.twingate.com/download"
echo "  2. Sign in with your @vay.io Google account"
echo "  3. Connect to the 'Vay Fleet' resource"
echo "     (Ask your team lead for the resource name if unsure)"
echo ""
read -rp "  Press Enter once Twingate is installed and connected (or Enter to skip for fixture/demo mode)..."

# ─── Step 2: System tools ───────────────────────────────────────────────────
step "Step 2/6 — System tools (Homebrew, Python 3.11, Node 20, Git)"

if ! command -v brew &>/dev/null; then
    echo "  Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
    fi
    ok "Homebrew installed"
else
    ok "Homebrew already installed"
fi

if ! command -v python3 &>/dev/null || ! python3 -c "import sys; assert sys.version_info >= (3,11)" 2>/dev/null; then
    echo "  Installing Python 3.11..."
    brew install python@3.11
    ok "Python 3.11 installed"
else
    ok "Python $(python3 --version) already installed"
fi

if ! command -v node &>/dev/null; then
    echo "  Installing Node..."
    brew install node
    ok "Node $(node --version) installed"
else
    ok "Node $(node --version) already installed"
fi

if ! command -v git &>/dev/null; then
    brew install git && ok "Git installed"
else
    ok "Git already installed"
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
open "https://github.com/settings/ssh/new" 2>/dev/null || true
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
    if git clone git@github.com:vay/ree-vehicle-configs.git "$INVENTORY_PATH"; then
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
open "https://vayio.atlassian.net/servicedesk/customer/portals" 2>/dev/null || true
echo ""
read -rp "  Path to fleet SSH private key   (Enter to skip — uses fixture mode): " FLEET_KEY
read -rp "  Path to fleet known_hosts file  (Enter to skip — uses fixture mode): " FLEET_HOSTS

# Determine executor mode
if [[ -n "$FLEET_KEY" && -n "$FLEET_HOSTS" ]]; then
    EXECUTOR="ssh"
else
    EXECUTOR="fixture"
fi

# Write .env (read natively by the backend via pydantic-settings)
cat > .env << EOF
# VayOBD runtime configuration — generated by scripts/setup-mac.sh
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

# run-dev.sh — starts Vite dev server + backend with fixture executor override
cat > run-dev.sh << 'DEVSCRIPT'
#!/usr/bin/env bash
# Start VayOBD in development mode (fixture executor, Vite on :5173, API on :8000)
# Usage: VAYOBD_DEV_USER=you@vay.io ./run-dev.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$REPO_ROOT/.venv/bin/activate"

DEV_USER="${VAYOBD_DEV_USER:-dev@local}"
echo "Starting VayOBD (dev) as $DEV_USER ..."

# Backend — .env is loaded automatically; override executor to fixture for dev
VAYOBD_EXECUTOR=fixture \
    uvicorn vayobd.app:app --reload --port 8000 &
BACKEND_PID=$!
echo "✓ Backend  → http://localhost:8000"

# Frontend — Vite proxies /api/* to :8000
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

# run-prod.sh — builds SPA, serves everything from a single uvicorn process
cat > run-prod.sh << 'PRODSCRIPT'
#!/usr/bin/env bash
# Start VayOBD in production mode (built SPA served by uvicorn on :8000)
# Requires .env to have VAYOBD_EXECUTOR=ssh + SSH credentials configured.
# Usage: ./run-prod.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$REPO_ROOT/.venv/bin/activate"

# Build the frontend SPA into frontend/dist/
echo "Building frontend..."
cd "$REPO_ROOT/frontend"
npm run build
cd "$REPO_ROOT"
echo "✓ Frontend built → frontend/dist/"

# Enable static serving by pointing VAYOBD_STATIC_DIR at the build output.
# This can also be set permanently in .env instead.
export VAYOBD_STATIC_DIR="$REPO_ROOT/frontend/dist"

echo "Starting server..."
exec uvicorn vayobd.app:app --host 0.0.0.0 --port 8000
PRODSCRIPT
chmod +x run-prod.sh
ok "Created run-prod.sh"

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
