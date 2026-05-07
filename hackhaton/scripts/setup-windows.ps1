# VayOBD — New Developer Setup (Windows)
# Run from the repo root in PowerShell (as Administrator):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\setup-windows.ps1
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function Write-Step  { param($msg) Write-Host "`n▶ $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-Pause { param($msg) Write-Host $msg -ForegroundColor Yellow; Read-Host "  Press Enter to continue" | Out-Null }

$RepoRoot      = Split-Path -Parent $PSScriptRoot
$InventoryPath = "$env:USERPROFILE\.cache\vayobd\ree-vehicle-configs"
$VenvPath      = "$RepoRoot\.venv"

Write-Host ""
Write-Host "  ╔════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║   VayOBD — New Developer Setup (Windows)       ║" -ForegroundColor Green
Write-Host "  ╚════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Steps: Twingate → Tools → SSH key → Inventory → Dependencies → Config"
Write-Host ""
Read-Host "  Press Enter to begin" | Out-Null

# ─── Step 1: Twingate ───────────────────────────────────────────────────────
Write-Step "Step 1/6 — Twingate (fleet network access)"
Write-Host "  Twingate gives you access to the Vay fleet network."
Write-Host "  Without it, checks against live vehicles/telestations will fail."
Write-Host ""
Write-Host "  1. Download from: https://www.twingate.com/download" -ForegroundColor White
Write-Host "  2. Sign in with your @vay.io Google account"
Write-Host "  3. Connect to the 'Vay Fleet' resource"
Write-Host "     (Ask your team lead for the resource name if unsure)"
Write-Host ""
Write-Pause "Press Enter once Twingate is installed and connected (or Enter to skip for fixture/demo mode)..."

# ─── Step 2: System tools ───────────────────────────────────────────────────
Write-Step "Step 2/6 — System tools (Python 3.11, Node 20, Git)"

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "  winget not found — opening Microsoft Store to install App Installer..."
    Start-Process "ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1"
    Write-Pause "Install 'App Installer' from the Store, then press Enter to continue..."
}

# Refresh PATH helper
function Refresh-Path {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  Installing Git..."
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    Refresh-Path
    Write-Ok "Git installed"
} else {
    Write-Ok "Git already installed ($(git --version))"
}

$pythonOk = $false
try { if (& python --version 2>&1) -match "3\.1[1-9]") { $pythonOk = $true } } catch {}
if (-not $pythonOk) {
    Write-Host "  Installing Python 3.11..."
    winget install --id Python.Python.3.11 -e --source winget --accept-package-agreements --accept-source-agreements
    Refresh-Path
    Write-Ok "Python 3.11 installed"
} else {
    Write-Ok "Python already installed"
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "  Installing Node 20..."
    winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-package-agreements --accept-source-agreements
    Refresh-Path
    Write-Ok "Node $(node --version) installed"
} else {
    Write-Ok "Node $(node --version) already installed"
}

# ─── Step 3: SSH key ────────────────────────────────────────────────────────
Write-Step "Step 3/6 — SSH key setup"

$SshDir = "$env:USERPROFILE\.ssh"
$SshKey = "$SshDir\id_ed25519"
if (-not (Test-Path $SshDir)) { New-Item -ItemType Directory -Path $SshDir | Out-Null }

if (-not (Test-Path $SshKey)) {
    Write-Host "  No SSH key found — generating a new one."
    $VayEmail = Read-Host "  Enter your Vay email address"
    ssh-keygen -t ed25519 -C $VayEmail -f $SshKey -N '""'
    Write-Ok "SSH key generated at $SshKey"
} else {
    Write-Ok "SSH key already exists at $SshKey"
}

try { Start-Service ssh-agent -ErrorAction SilentlyContinue; ssh-add $SshKey 2>$null } catch {}

Write-Host ""
Write-Host "  Your public key (copy this):" -ForegroundColor White
Write-Host "  ┌──────────────────────────────────────────────────────────────┐"
Get-Content "$SshKey.pub" | ForEach-Object { Write-Host "  │ $_" }
Write-Host "  └──────────────────────────────────────────────────────────────┘"
Write-Host ""
Write-Host "  Add it to GitHub: https://github.com/settings/ssh/new" -ForegroundColor Yellow
Start-Process "https://github.com/settings/ssh/new"
Write-Host ""
Write-Pause "Press Enter once you've added the key to GitHub..."

Write-Host "  Testing GitHub SSH connection..."
if ((ssh -o StrictHostKeyChecking=no -T git@github.com 2>&1) -match "successfully authenticated") {
    Write-Ok "GitHub SSH connection verified"
} else {
    Write-Warn "Could not verify GitHub connection — continuing anyway."
}

# ─── Step 4: Vehicle inventory ──────────────────────────────────────────────
Write-Step "Step 4/6 — Vehicle inventory (ree-vehicle-configs)"

$CacheDir = "$env:USERPROFILE\.cache\vayobd"
if (-not (Test-Path $CacheDir)) { New-Item -ItemType Directory -Path $CacheDir | Out-Null }

if (Test-Path "$InventoryPath\.git") {
    Write-Ok "Inventory already cloned — pulling latest..."
    try { git -C $InventoryPath pull --ff-only } catch { Write-Warn "Could not pull (continuing with cached version)" }
} else {
    Write-Host "  Cloning ree-vehicle-configs..."
    try {
        git clone git@github.com:vay/ree-vehicle-configs.git $InventoryPath
        Write-Ok "Inventory cloned"
    } catch {
        Write-Warn "Could not clone ree-vehicle-configs (no GitHub access yet?)."
        Write-Warn "Re-run this script after your GitHub access is granted."
    }
}

# ─── Step 5: Backend + frontend dependencies ────────────────────────────────
Write-Step "Step 5/6 — Backend (Python) and frontend (Node) dependencies"

Set-Location $RepoRoot
if (-not (Test-Path $VenvPath)) { python -m venv $VenvPath }
& "$VenvPath\Scripts\python.exe" -m pip install -e backend --quiet
Write-Ok "Backend installed"

Set-Location "$RepoRoot\frontend"
npm install --silent
Write-Ok "Frontend dependencies installed"

# ─── Step 6: .env + launchers ───────────────────────────────────────────────
Write-Step "Step 6/6 — Configuration and run scripts"

Set-Location $RepoRoot

Write-Host "  Fleet SSH credentials are needed to run checks against real hosts."
Write-Host "  Request them via the Vay IT Service Desk:" -ForegroundColor Yellow
Write-Host "    → https://vayio.atlassian.net/servicedesk/customer/portals" -ForegroundColor Cyan
Start-Process "https://vayio.atlassian.net/servicedesk/customer/portals"
Write-Host ""
$FleetKey   = Read-Host "  Path to fleet SSH private key   (Enter to skip — uses fixture mode)"
$FleetHosts = Read-Host "  Path to fleet known_hosts file  (Enter to skip — uses fixture mode)"

$Executor = if ($FleetKey -and $FleetHosts) { "ssh" } else { "fixture" }
$FleetBlock = if ($FleetKey -and $FleetHosts) {
    "VAYOBD_SSH_KEY=$FleetKey`nVAYOBD_SSH_KNOWN_HOSTS=$FleetHosts"
} else { "" }

# Write .env
@"
# VayOBD runtime configuration — generated by scripts/setup-windows.ps1
# Edit any value here; changes take effect on next server restart.
# See .env.example for all available options.

VAYOBD_EXECUTOR=$Executor
VAYOBD_INVENTORY_PATH=$InventoryPath
$FleetBlock

# Uncomment when running in production (after npm run build in frontend/):
# VAYOBD_STATIC_DIR=./frontend/dist
"@ | Set-Content "$RepoRoot\.env" -Encoding UTF8
Write-Ok "Created .env"

# run-dev.ps1
@"
# Start VayOBD in development mode (fixture executor, Vite on :5173, API on :8000)
# Usage: `$env:VAYOBD_DEV_USER = "you@vay.io"; .\run-dev.ps1

`$RepoRoot = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$DevUser  = if (`$env:VAYOBD_DEV_USER) { `$env:VAYOBD_DEV_USER } else { "dev@local" }

Write-Host "Starting VayOBD (dev) as `$DevUser ..."

# .env is loaded automatically by the backend; override executor to fixture for dev
`$env:VAYOBD_EXECUTOR = "fixture"

`$backendProcess = Start-Process -FilePath "$VenvPath\Scripts\uvicorn.exe" ``
    -ArgumentList "vayobd.app:app", "--reload", "--port", "8000" ``
    -WorkingDirectory `$RepoRoot -PassThru -NoNewWindow
Write-Host "✓ Backend  → http://localhost:8000" -ForegroundColor Green

`$env:VAYOBD_DEV_USER = `$DevUser
`$frontendProcess = Start-Process -FilePath "npm.cmd" ``
    -ArgumentList "run", "dev" ``
    -WorkingDirectory "`$RepoRoot\frontend" -PassThru -NoNewWindow
Write-Host "✓ Frontend → http://localhost:5173" -ForegroundColor Green

Write-Host "`nPress Ctrl+C to stop." -ForegroundColor Yellow
try {
    Wait-Process -Id `$backendProcess.Id, `$frontendProcess.Id
} finally {
    Stop-Process -Id `$backendProcess.Id  -ErrorAction SilentlyContinue
    Stop-Process -Id `$frontendProcess.Id -ErrorAction SilentlyContinue
    Write-Host "Stopped."
}
"@ | Set-Content "$RepoRoot\run-dev.ps1" -Encoding UTF8
Write-Ok "Created run-dev.ps1"

# run-prod.ps1
@"
# Start VayOBD in production mode (built SPA served by uvicorn on :8000)
# Requires .env to have VAYOBD_EXECUTOR=ssh + SSH credentials configured.
# Usage: .\run-prod.ps1

`$RepoRoot = Split-Path -Parent `$MyInvocation.MyCommand.Path

Write-Host "Building frontend..."
Push-Location "`$RepoRoot\frontend"
npm run build
Pop-Location
Write-Host "✓ Frontend built → frontend\dist\" -ForegroundColor Green

`$env:VAYOBD_STATIC_DIR = "`$RepoRoot\frontend\dist"

Write-Host "Starting server..."
& "$VenvPath\Scripts\uvicorn.exe" vayobd.app:app --host 0.0.0.0 --port 8000
"@ | Set-Content "$RepoRoot\run-prod.ps1" -Encoding UTF8
Write-Ok "Created run-prod.ps1"

# ─── Done ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  ✓ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Development (fixture mode, Vite hot-reload):"
Write-Host '    $env:VAYOBD_DEV_USER = "you@vay.io"; .\run-dev.ps1' -ForegroundColor White
Write-Host "    → http://localhost:5173"
Write-Host ""
Write-Host "  Production (built SPA, live SSH executor):"
Write-Host "    .\run-prod.ps1" -ForegroundColor White
Write-Host "    → http://localhost:8000"
Write-Host ""
Write-Host "  Settings: edit .env (see .env.example for all options)"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
