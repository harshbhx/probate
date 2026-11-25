# Probate monorepo. `make help` lists everything.
PY      := services/core/.venv/bin/python
SIMDATA := .data/sim

.PHONY: help setup dev api web site test lint sim build serve deploy deploy-check site-deploy ship clean

help: ## Show this list
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-13s %s\n", $$1, $$2}'

setup: ## Install Python and web dependencies
	cd services/core && python3 -m venv .venv && .venv/bin/pip install -q -e '.[dev]'
	npm install

sim: ## Simulate 12 generations locally with stand-in models
	rm -rf $(SIMDATA)
	PROBATE_FAKE=1 PROBATE_DATA_DIR=$(SIMDATA) $(PY) -m probate.courthouse.simulate --generations 12

api: ## Run the API on :8080 against the simulated family
	cd services/core && PROBATE_FAKE=1 PROBATE_DATA_DIR=../../$(SIMDATA) .venv/bin/uvicorn probate.courthouse.app:app --port 8080 --reload

web: ## Run the website with hot reload on :5173 (proxies /api to :8080)
	npm run dev

site: ## The landing page and docs (Fumadocs) on :3001
	npm run dev -w @probate/site

dev: ## API and website together
	@$(MAKE) -j2 api web

test: ## Python tests
	cd services/core && PROBATE_DATA_DIR=$$(mktemp -d) .venv/bin/python -m pytest -q

lint: ## Ruff and TypeScript for every app
	cd services/core && .venv/bin/ruff check probate tests ../../scripts
	npm run lint -w @probate/web
	npm run lint -w @probate/site

build: ## Build the live site (apps/web/dist) and the landing + docs (apps/site/out)
	npm run build -w @probate/web
	npm run build -w @probate/site

serve: ## The built live site and API on :8080, the way the Courthouse serves it
	npm run build -w @probate/web
	cd services/core && PROBATE_FAKE=1 PROBATE_DATA_DIR=../../$(SIMDATA) .venv/bin/uvicorn probate.courthouse.app:app --port 8080

deploy-check: ## Validate .env and the bundle without touching Sprites
	npm run build -w @probate/web
	$(PY) scripts/deploy.py --check

deploy: ## Deploy or update the Courthouse Sprite
	npm run build -w @probate/web
	$(PY) scripts/deploy.py

site-deploy: ## Build the landing + docs and deploy them to Cloudflare (needs `npx wrangler login`)
	npm run build -w @probate/site
	cd apps/site && npx wrangler deploy

ship: ## Test, build, create the GitHub repo, push, deploy
	bash scripts/ship.sh

clean: ## Remove local data and build output
	rm -rf .data apps/web/dist apps/site/out apps/site/.next apps/site/.source
