#!/usr/bin/env bash
# One command to go public:  make ship   (or  bash scripts/ship.sh [repo-name])
#
# 1. checks: tests, lint, type check, web build, no secrets staged
# 2. creates the GitHub repo if it doesn't exist (public, via `gh`), adds `origin`, pushes main
# 3. deploys the Courthouse to Fly.io Sprites if services/core/.env exists
#
# Needs: `gh auth login` done once. Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPO="${1:-probate}"
PY="services/core/.venv/bin/python"

say() { printf '\n\033[1m→ %s\033[0m\n' "$*"; }
die() { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

command -v gh >/dev/null || die "Install the GitHub CLI first: https://cli.github.com"
gh auth status >/dev/null 2>&1 || die "Run 'gh auth login' once, then re-run this."
# Pushing .github/workflows needs the `workflow` scope, which gh doesn't grant by default.
if ! gh auth status 2>&1 | grep -q "workflow"; then
  say "Asking GitHub for the 'workflow' scope (needed to push the CI file)"
  gh auth refresh -h github.com -s workflow
fi
gh auth setup-git >/dev/null 2>&1 || true
[ -x "$PY" ] || die "Python env missing. Run 'make setup' first."

say "Checking for secrets"
for f in services/core/.env config/owner.yaml; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then die "$f is tracked by git. Remove it from the index first."; fi
done
if git grep -nE '(sk-ant-|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,})' -- ':!*.lock' ':!package-lock.json' >/dev/null; then
  die "Something that looks like an API key is committed. Run: git grep -nE 'sk-|AKIA|ghp_'"
fi

say "Tests and lint"
(cd services/core && PROBATE_DATA_DIR="$(mktemp -d)" .venv/bin/python -m pytest -q && .venv/bin/ruff check probate)

say "Building the website"
npm run build --silent

say "Committing anything left over"
git add -A
git diff --cached --quiet || git commit -q -m "Prepare release"

OWNER="$(gh api user -q .login)"
say "GitHub: $OWNER/$REPO"
if ! gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  gh repo create "$OWNER/$REPO" --public \
    --description "My agent dies every night. A court decides what its child inherits. Built on Fly.io Sprites." \
    --homepage "https://fly.io/hacksgiving/"
fi
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$REPO.git"
git branch -M main
git push -u origin main
gh repo edit "$OWNER/$REPO" --add-topic hacksgiving --add-topic fly-io --add-topic sprites --add-topic ai-agents >/dev/null || true

if [ -f services/core/.env ]; then
  say "Deploying the Courthouse to Sprites"
  "$PY" scripts/deploy.py
else
  say "Skipping deploy: services/core/.env doesn't exist yet (copy .env.example and fill it in)"
fi

say "Done. Repo: https://github.com/$OWNER/$REPO"
