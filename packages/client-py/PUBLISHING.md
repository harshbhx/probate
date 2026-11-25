# Publishing probate-client (PyPI)

Run these yourself. No token belongs in the repo or in this file.

1. Check the name is still free: `curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/probate-client/json` should print 404.
2. From `packages/client-py`, in a clean venv: `pip install -e '.[dev]' -e ../../services/core`, then `ruff check .` and `pytest`.
3. Set the version in `pyproject.toml` and `src/probate_client/__init__.py`; move the CHANGELOG entry from "unreleased" to a date.
4. Build: `rm -rf dist && python -m build`
5. Check: `twine check dist/*`
6. Try it first on TestPyPI (needs a separate account and API token from test.pypi.org):
   `twine upload --repository testpypi dist/*`
   then in a fresh venv `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ probate-client`.
7. Upload for real: `twine upload dist/*`
   When prompted, the username is `__token__` and the password is your pypi.org API token (scope it to this project after the first upload). Or put it in `~/.pypirc`, outside the repo.
8. Verify in a fresh venv: `pip install probate-client && python -c "import probate_client; print(probate_client.__version__)"`.
9. Tag: `git tag client-py-v0.1.0 && git push origin client-py-v0.1.0`.

PyPI never lets you re-upload a version. If something is wrong, yank the release and publish a new patch version.
