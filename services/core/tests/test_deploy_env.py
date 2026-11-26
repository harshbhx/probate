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
