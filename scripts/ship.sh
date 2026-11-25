#!/usr/bin/env bash
# One command to go public:  make ship   (or  bash scripts/ship.sh [repo-name])
#
# 1. checks: no secrets tracked, tests, lint, both sites build
# 2. GitHub: creates the public repo if needed (via `gh`) and pushes main
# 3. Sprites: deploys the Courthouse and the live-family site, if services/core/.env exists
# 4. Cloudflare: deploys the landing page and docs (apps/site) with Wrangler, if signed in
# 5. Links the two sites to each other (one extra Courthouse deploy the first time)
#
# Needs once: `gh auth login`, `npx wrangler login` (or CLOUDFLARE_API_TOKEN). Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPO="${1:-probate}"
# The venv puts its programs in bin/ on Linux and macOS and in Scripts/ on Windows (Git Bash).
if [ -d services/core/.venv/Scripts ]; then VENVBIN="Scripts"; else VENVBIN="bin"; fi
PY="services/core/.venv/$VENVBIN/python"
STATE=".data"
mkdir -p "$STATE"

say() { printf '\n\033[1m→ %s\033[0m\n' "$*"; }
note() { printf '  %s\n' "$*"; }
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

# ---------------------------------------------------------------- 1. checks
say "Checking for secrets"
for f in services/core/.env config/owner.yaml; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then die "$f is tracked by git. Remove it from the index first."; fi
done
if git grep -nE '(sk-ant-|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,})' -- ':!*.lock' ':!package-lock.json' >/dev/null; then
  die "Something that looks like an API key is committed. Run: git grep -nE 'sk-|AKIA|ghp_'"
fi

say "Tests and lint"
(cd services/core && PROBATE_DATA_DIR="$(mktemp -d)" .venv/$VENVBIN/python -m pytest -q && .venv/$VENVBIN/ruff check probate tests ../../scripts)
npm run lint --silent

say "Building both sites"
npm run build --silent

say "Checking the working tree is clean"
if [ -n "$(git status --porcelain)" ]; then
  git status --short
  die "The working tree has uncommitted changes. Commit them on a branch (with a PR) first, then re-run."
fi

# ---------------------------------------------------------------- 2. GitHub
OWNER="$(gh api user -q .login)"
GH_REPO="$OWNER/$REPO"
say "GitHub: $GH_REPO"
if ! gh repo view "$GH_REPO" >/dev/null 2>&1; then
  gh repo create "$GH_REPO" --public \
    --description "My agent dies every night. A court decides what its child inherits. Built on Fly.io Sprites." \
    --homepage "https://fly.io/hacksgiving/"
fi
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$GH_REPO.git"
git branch -M main
git push -u origin main
gh repo edit "$GH_REPO" --add-topic hacksgiving --add-topic fly-io --add-topic sprites --add-topic ai-agents >/dev/null || true

# ---------------------------------------------------------------- 3. Sprites
LIVE_URL=""
SITE_URL="$(cat "$STATE/site-url.txt" 2>/dev/null || true)"
if [ -f services/core/.env ]; then
  say "Deploying the Courthouse to Sprites"
  VITE_DOCS_URL="$SITE_URL" VITE_REPO_URL="https://github.com/$GH_REPO" npm run build -w @probate/web --silent
  "$PY" scripts/deploy.py
  LIVE_URL="$(cat "$STATE/courthouse-url.txt" 2>/dev/null || true)"
else
  say "Skipping Sprites: services/core/.env doesn't exist yet (copy .env.example and fill it in)"
fi

# ---------------------------------------------------------------- 4. Cloudflare
deploy_site() {
  NEXT_PUBLIC_LIVE_URL="$LIVE_URL" NEXT_PUBLIC_GITHUB_REPO="$GH_REPO" NEXT_PUBLIC_SITE_URL="$1" \
    npm run build -w @probate/site --silent
  (cd apps/site && npx wrangler deploy 2>&1) | tee "$STATE/wrangler.log"
}

if [ -n "${CLOUDFLARE_API_TOKEN:-}" ] || (cd apps/site && npx wrangler whoami 2>/dev/null | grep -qi "associated with"); then
  say "Deploying the landing page and docs to Cloudflare"
  deploy_site "${SITE_URL:-https://example.invalid}"
  NEW_URL="$(grep -oE 'https://[a-zA-Z0-9.-]+\.workers\.dev' "$STATE/wrangler.log" | tail -1 || true)"
  if [ -n "$NEW_URL" ] && [ "$NEW_URL" != "$SITE_URL" ]; then
    # First deploy: now that the address is known, rebuild so links and previews use it,
    # and give the live site its "Docs" link.
    echo "$NEW_URL" > "$STATE/site-url.txt"
    SITE_URL="$NEW_URL"
    say "Linking the two sites"
    deploy_site "$SITE_URL"
    if [ -n "$LIVE_URL" ]; then
      VITE_DOCS_URL="$SITE_URL" VITE_REPO_URL="https://github.com/$GH_REPO" npm run build -w @probate/web --silent
      "$PY" scripts/deploy.py
    fi
  fi
else
  say "Skipping Cloudflare: run 'npx wrangler login' once (or set CLOUDFLARE_API_TOKEN), then re-run"
fi

[ -n "$SITE_URL" ] && gh repo edit "$GH_REPO" --homepage "$SITE_URL" >/dev/null 2>&1 || true

# ---------------------------------------------------------------- done
say "Done"
note "Code:         https://github.com/$GH_REPO"
[ -n "$LIVE_URL" ] && note "Live family:  $LIVE_URL"
[ -n "$SITE_URL" ] && note "Landing+docs: $SITE_URL"
true
