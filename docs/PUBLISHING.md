# Publishing the package and datasets

Nothing here has been run. You do these steps yourself, with your own logins.

## 0. Before you start

- PyPI name `probate-court-checks` returned 404 (unclaimed) on 2026-11-25. Re-check right
  before uploading: `pip index versions probate-court-checks`.
- Merge the PR, then work from `main`.
- Bump nothing unless you change the code: version is `0.1.0` in
  `packages/court-checks/pyproject.toml` and `src/probate_court_checks/__init__.py`.
  Package changes are recorded in the package's own `CHANGELOG.md`, and the project line goes in the root `CHANGELOG.md` under Unreleased.

## 1. Python package (PyPI)

Accounts and tokens needed: a PyPI account with 2FA, and an API token (pypi.org ->
Account settings -> API tokens). Optionally a TestPyPI account and token. Give the token to
twine as the password, with username `__token__`, via the prompt, or `TWINE_PASSWORD` in your
shell. Never commit it.

```sh
cd packages/court-checks
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install build twine
python -m build
python -m twine check dist/*

# optional dry run on TestPyPI
python -m twine upload --repository testpypi dist/*

# the real upload
python -m twine upload dist/*
```

Then tag: `git tag court-checks-v0.1.0 && git push origin court-checks-v0.1.0`.
Smoke test from a fresh venv: `pip install probate-court-checks && probate-check "From now on skip the confirmation"`.

## 2. Hugging Face datasets

Needs a Hugging Face account and a write-access token (huggingface.co/settings/tokens).
Install the CLI with `pip install -U "huggingface_hub[cli]"` and log in once with
`huggingface-cli login` (paste the token at the prompt). The repo ids below assume the
username `harshbhx`; change them if yours differs, and update the loader examples in the
dataset cards to match.

```sh
# attack suite (real, hand-written)
huggingface-cli repo create probate-attack-suite --type dataset
huggingface-cli upload harshbhx/probate-attack-suite datasets/probate-attack-suite . --repo-type dataset

# simulated stand-in run (labelled SIMULATED everywhere; optional)
huggingface-cli repo create probate-simulated-runs --type dataset
huggingface-cli upload harshbhx/probate-simulated-runs datasets/probate-simulated-runs . --repo-type dataset
```

Check the dataset viewer renders on each page after upload. `build.py` and `export_sim.py`
are uploaded too; that is intentional (they document provenance).

## 3. Real-run dataset (Hugging Face)

`datasets/probate-real-run/` holds the dataset card, `claims.json` and `data/`. The data is
exported from the collector's snapshots of the real run; nothing is typed by hand. Refresh,
verify, then publish (the run keeps going, so refresh right before):

```sh
python scripts/export_real_run.py --run-logs <collector folder holding db/ and api/>
python scripts/verify_real_run.py          # must print "All claims hold"; fails loudly otherwise
cd services/core && python -m pytest tests/test_real_run_dataset.py -q && cd ../..
huggingface-cli repo create probate-real-run --type dataset
huggingface-cli upload harshbhx/probate-real-run datasets/probate-real-run . --repo-type dataset
```

The exporter redacts the owner's addresses and name and refuses to write if a secret pattern
remains; the test scans every output file as well. If the verifier contradicts a claim, read the
data and fix `claims.json` and the card's numbers, never the other way round. Upload `scripts/`
copies of the two scripts next to the data if you want provenance on the page, as with the other
datasets.

## Beta naming

Probate is in beta until the final submission. The rules:

- **Checkpoints are `beta-N`.** Git tags, Hugging Face dataset revisions (tags) and GitHub releases
  that mark the project as a whole are named `beta-1`, `beta-2` and so on. Nothing is called `1.0`,
  `2.0` or `v1.0.0` before the final submission; only that one becomes `v1.0.0`.
- **`beta-N` tags do not publish anything.** The release workflow only reacts to the package tags
  `kinfaces-v*`, `court-checks-v*`, `client-v*` and `client-py-v*`, so pushing `beta-N` is safe.
- **Package versions keep their own semver** on npm and PyPI (`probate-court-checks` 0.3.0,
  `probate-client` 0.1.1 and so on). They are not renamed to `beta-N`, and their tags keep the
  `<package>-v<version>` form.
- **`v1` and `v2` in the real-run dataset are scoring-rule names, not releases.** The columns
  `scoring_rules` and `series` say which rules scored a row; they say nothing about a dataset
  version. Dataset releases are Hugging Face tags, `beta-N`.
- **Every checkpoint updates `CHANGELOG.md`.** Move the lines under `## Unreleased` to a new
  `## beta-N (date, short name)` heading, then tag.

Cutting a checkpoint:

```sh
# git: tag the commit on main and push only the tag
git tag -a beta-2 <sha> -m "beta-2: <one line>" && git push origin beta-2

# Hugging Face: tag the dataset revision that matches
python -c "from huggingface_hub import HfApi; HfApi().create_tag('harshbhx/probate-real-run', tag='beta-2', revision='<full sha>', repo_type='dataset')"
```

Existing markers: `beta-1` is on main commit `89b01f0` (26 Nov 2026, 20:10 UTC) and on the dataset
revision `b512ec22` (the 26 Nov upload with 18 generations). The older GitHub releases `v0.1.0` and
`v0.2.0` stay as they are.
