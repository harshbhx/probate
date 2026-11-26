"""The Courthouse sources its .env with bash, so scripts/deploy.py must write shell-safe values."""

import importlib.util
import shlex
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[3] / "scripts" / "deploy.py"


def _load():
    spec = importlib.util.spec_from_file_location("deploy_script", DEPLOY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        key, _, raw = line.partition("=")
        (value,) = shlex.split(raw) if raw else [""]
        out[key] = value
    return out


def test_json_and_placeholders_survive_the_shell():
    deploy = _load()
    env = {
        "PROBATE_SPRITES_TOKEN": "t",
        "PROBATE_CONNECTIONS": '{"box":"abc","cloudflare":"custom_api/xyz"}',
        "TYPESAFE_BASE_URL": "https://example.test/<connection_id>",
        "PROBATE_NOTE": "it's a $HOME & `date` test",
    }
    text = deploy.render_env(env).decode()
    back = _parse(text)
    assert back["PROBATE_CONNECTIONS"] == env["PROBATE_CONNECTIONS"]
    assert back["TYPESAFE_BASE_URL"] == env["TYPESAFE_BASE_URL"]
    assert back["PROBATE_NOTE"] == env["PROBATE_NOTE"]
    assert back["PROBATE_FAKE"] == "0"  # the live settings are still added


class _FakeApi:
    def __init__(self, existing: bytes | None = None) -> None:
        self.files = {} if existing is None else {"data/probate.db": existing}
        self.writes: list[str] = []

    def read_file(self, name, path):
        return self.files.get(path)

    def write_file(self, name, path, data, mode="0644"):
        self.files[path] = data
        self.writes.append(path)


def _db(tmp_path):
    import sqlite3

    p = tmp_path / "probate.db"
    c = sqlite3.connect(p)
    c.execute("create table t (x)")
    c.commit()
    c.close()
    return p


def test_restore_puts_a_saved_database_on_a_new_courthouse(tmp_path):
    deploy = _load()
    api = _FakeApi()
    said = deploy.restore_database(api, "c", _db(tmp_path))
    assert api.writes == ["data/probate.db"] and said.startswith("restored")
    assert api.files["data/probate.db"].startswith(b"SQLite format 3")


def test_restore_never_overwrites_a_database_that_exists(tmp_path):
    deploy = _load()
    api = _FakeApi(existing=b"SQLite format 3 live data")
    said = deploy.restore_database(api, "c", _db(tmp_path))
    assert api.writes == [] and "left it alone" in said
    assert api.files["data/probate.db"] == b"SQLite format 3 live data"


def test_restore_refuses_a_file_that_is_not_a_database(tmp_path):
    import pytest

    deploy = _load()
    bad = tmp_path / "x.db"
    bad.write_text("not a database")
    with pytest.raises(SystemExit):
        deploy.restore_database(_FakeApi(), "c", bad)
