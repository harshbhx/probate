#!/usr/bin/env bash
# Runs once when the Codespace / dev container is created. Fails loudly: every step is logged and any error stops the script.
set -euo pipefail

cd "$(dirname "$0")/.."
step() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
trap 'fail "post-create failed at line $LINENO (see the log above). Re-run it with: bash .devcontainer/post-create.sh"' ERR

step "Checking toolchain"
command -v node >/dev/null || fail "node is not on PATH. Rebuild the container (Codespaces: Ctrl+Shift+P, 'Rebuild Container')."
command -v python3 >/dev/null || fail "python3 is not on PATH."
node -v; npm -v; python3 --version
# Some dependencies (undici 8, chokidar 6) need Node >= 22.22; the apps need >= 20.19.
node -e '
const [maj, min] = process.versions.node.split(".").map(Number);
if (maj < 22 || (maj === 22 && min < 22)) {
  console.error("Node " + process.versions.node + " is too old: this repo needs Node >= 22.22 (CI uses 22).");
  process.exit(1);
}' || fail "Wrong Node version. Rebuild the container so the Node 22 feature is re-resolved."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || fail "Python >= 3.11 is required."

step "Python virtualenv and services/core (pip install -e .[dev])"
rm -rf services/core/.venv
python3 -m venv services/core/.venv
services/core/.venv/bin/python -m pip install --quiet --disable-pip-version-check -e 'services/core[dev]'

step "JavaScript workspaces (npm ci, exact versions from package-lock.json)"
npm ci --no-audit --no-fund

step "Simulating a 12-generation family with stand-in models (no keys, nothing leaves the container)"
make sim

step "Building the live site so 'make serve' starts fast"
npm run build -w @probate/web

printf '\nAll set. The live family site starts on port 8080 (Ports tab). Run "make help" for every command.\n'
