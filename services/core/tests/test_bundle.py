import io
import tarfile

from probate.common.bundle import make_bundle


def _names(tmp_path, **kw):
    root = tmp_path / "repo"
    core = root / "services" / "core"
    (core / "probate").mkdir(parents=True)
    (core / "probate" / "__init__.py").write_text("")
    (core / ".env").write_text("PROBATE_SPRITES_TOKEN=secret")
    (core / ".venv" / "lib").mkdir(parents=True)
    (core / "probate" / "__pycache__").mkdir()
    (core / "tests").mkdir()
    (root / "config").mkdir()
    (root / "config" / "names.yaml").write_text("names: []")
    dist = root / "apps" / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html>")
    data = make_bundle(root, **kw)
    return tarfile.open(fileobj=io.BytesIO(data)).getnames()


def test_bundle_never_carries_secrets_or_envs(tmp_path):
    names = _names(tmp_path, web=True)
    assert "services/core/probate/__init__.py" in names
    assert "config/names.yaml" in names
    assert "apps/web/dist/index.html" in names
    assert not any(n.endswith(".env") or ".venv" in n or "__pycache__" in n for n in names)
    assert not any(n.startswith("services/core/tests") for n in names)


def test_generation_bundle_has_no_website(tmp_path):
    assert not any(n.startswith("apps/") for n in _names(tmp_path))
