# Probate monorepo. `make help` lists everything.
PY      := services/core/.venv/bin/python
SIMDATA := .data/sim

.PHONY: help setup dev api web test lint sim build serve deploy deploy-check ship clean

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

dev: ## API and website together
	@$(MAKE) -j2 api web

test: ## Python tests
	cd services/core && PROBATE_DATA_DIR=$$(mktemp -d) .venv/bin/python -m pytest -q

lint: ## Ruff and TypeScript
	cd services/core && .venv/bin/ruff check probate tests ../../scripts
	npm run lint

build: ## Build the website into apps/web/dist
	npm run build

serve: build ## The built site and API on :8080, the way the Courthouse serves it
	cd services/core && PROBATE_FAKE=1 PROBATE_DATA_DIR=../../$(SIMDATA) .venv/bin/uvicorn probate.courthouse.app:app --port 8080

deploy-check: build ## Validate .env and the bundle without touching Sprites
	$(PY) scripts/deploy.py --check

deploy: build ## Deploy or update the Courthouse Sprite
	$(PY) scripts/deploy.py

ship: ## Test, build, create the GitHub repo, push, deploy
	bash scripts/ship.sh

clean: ## Remove local data and build output
	rm -rf .data apps/web/dist
