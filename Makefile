# Probate monorepo. `make help` lists everything.
# The venv puts its programs in bin/ on Linux and macOS and in Scripts/ on Windows (Git Bash).
VENVBIN := $(if $(wildcard services/core/.venv/Scripts),Scripts,bin)
PY      := services/core/.venv/$(VENVBIN)/python
PYTHON  := $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)
SIMDATA := .data/sim
# Addresses baked into the real builds so links, social cards and the Docs link point at the deployed sites.
REPO      ?= harshbhx/probate
SITE_URL  ?= $(shell cat .data/site-url.txt 2>/dev/null)
LIVE_URL  ?= $(shell cat .data/courthouse-url.txt 2>/dev/null)
WEB_ENV   := VITE_DOCS_URL="$(SITE_URL)" VITE_REPO_URL="https://github.com/$(REPO)"
SITE_ENV  := NEXT_PUBLIC_SITE_URL="$(or $(SITE_URL),https://example.invalid)" NEXT_PUBLIC_LIVE_URL="$(LIVE_URL)" NEXT_PUBLIC_GITHUB_REPO="$(REPO)"

.PHONY: help setup dev api web site api-spec site-data agent-examples site-shots test lint sim build serve deploy deploy-check site-deploy ship clean

help: ## Show this list
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-13s %s\n", $$1, $$2}'

setup: ## Install Python and web dependencies
	cd services/core && $(PYTHON) -m venv .venv && "$$([ -d .venv/Scripts ] && echo .venv/Scripts || echo .venv/bin)/python" -m pip install -q -e '.[dev]'
	npm install

sim: ## Simulate 12 generations locally with stand-in models
	rm -rf $(SIMDATA)
	PROBATE_FAKE=1 PROBATE_DATA_DIR=$(SIMDATA) $(PY) -m probate.courthouse.simulate --generations 12

api: ## Run the API on :8080 against the simulated family
	cd services/core && PROBATE_FAKE=1 PROBATE_DATA_DIR=../../$(SIMDATA) .venv/$(VENVBIN)/uvicorn probate.courthouse.app:app --port 8080 --reload

web: ## Run the website with hot reload on :5173 (proxies /api to :8080)
	npm run dev

site: ## The landing page and docs (Fumadocs) on :3001
	npm run dev -w @probate/site

dev: ## API and website together
	@$(MAKE) -j2 api web

test: ## Python tests and the family-face model
	cd services/core && PROBATE_DATA_DIR=$$(mktemp -d) .venv/$(VENVBIN)/python -m pytest -q
	npm test -w kinfaces --silent

lint: ## Ruff and TypeScript for every app
	cd services/core && .venv/$(VENVBIN)/ruff check probate tests ../../scripts
	npm run lint -w @probate/web
	npm run lint -w @probate/site

build: ## Build the live site (apps/web/dist) and the landing + docs (apps/site/out)
	npm run build -w @probate/web
	npm run build -w @probate/site

serve: ## The built live site and API on :8080, the way the Courthouse serves it
	npm run build -w @probate/web
	cd services/core && PROBATE_FAKE=1 PROBATE_DATA_DIR=../../$(SIMDATA) .venv/$(VENVBIN)/uvicorn probate.courthouse.app:app --port 8080

deploy-check: ## Validate .env and the bundle without touching Sprites
	$(WEB_ENV) npm run build -w @probate/web
	$(PY) scripts/deploy.py --check

deploy: ## Deploy or update the Courthouse Sprite
	$(WEB_ENV) npm run build -w @probate/web
	$(PY) scripts/deploy.py

api-spec: ## Re-export the API schema the docs reference is built from (apps/site/openapi.json)
	$(PY) scripts/export_openapi.py

site-data: ## Re-export the court examples the landing page shows (from the real layer-1 code)
	$(PY) scripts/export_site_data.py

agent-examples: ## Re-export the memory court and Page Court examples (needs packages/memory-court and beautifulsoup4)
	python3 scripts/export_agent_examples.py

site-shots: ## Re-capture the landing page product shots (needs make serve running and Playwright)
	$(PYTHON) scripts/product_shots.py

site-deploy: ## Build the landing + docs and deploy them to Cloudflare (needs `npx wrangler login`)
	$(SITE_ENV) npm run build -w @probate/site
	cd apps/site && npx wrangler deploy

ship: ## Everything: checks, GitHub, Sprites (Courthouse) and Cloudflare (landing + docs)
	bash scripts/ship.sh

clean: ## Remove local data and build output
	rm -rf .data apps/web/dist apps/site/out apps/site/.next apps/site/.source
