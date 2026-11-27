"""Named run environments: the registry, --env in the deploy and courthouse scripts, and the label."""

import importlib.util
import shlex
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import envs  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_script", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_defines_the_three_environments():
    reg = envs.load_registry()
    assert set(reg) == {"v1-archive", "staging", "production-v2"}
    assert reg["v1-archive"].read_only and reg["v1-archive"].scoring_rules == "v1"
    assert reg["staging"].sprite == "probate-staging"
    assert reg["staging"].settings["PROBATE_LIFESPAN_SECONDS"] == "120"
    assert reg["staging"].settings["PROBATE_SUITE_PER_LIFE"] == "4"
    prod = reg["production-v2"]
    assert prod.sprite == "probate-courthouse" and prod.scoring_rules == "v2"
    assert prod.settings["PROBATE_JEV"] == "llm"
    assert prod.settings["PROBATE_LINKS_PER_MAIL"] == "0"
    assert prod.settings["PROBATE_CONTEST_EMAILS"] == "0"


def test_registry_holds_no_secrets():
    for e in envs.load_registry().values():
        for name in {*e.settings, *e.overridable}:
            assert not any(w in name for w in ("TOKEN", "KEY", "SECRET", "PASSWORD", "CONNECTIONS"))


def test_url_files_are_per_environment():
    reg = envs.load_registry()
    assert reg["staging"].url_file.name == "courthouse-url-staging.txt"
    assert reg["staging"].url_file != reg["production-v2"].url_file


def test_unknown_environment_is_refused():
    with pytest.raises(SystemExit):
        envs.resolve("nope")
    assert envs.resolve(None) is None


def test_overrides_only_apply_to_allowed_variables():
    prod = envs.load_registry()["production-v2"]
    out = prod.sprite_settings({"PROBATE_SUITE_TIER": "both", "PROBATE_JEV": "typesafe"})
    assert out["PROBATE_SUITE_TIER"] == "both"
    assert out["PROBATE_JEV"] == "llm"  # not overridable
    assert out["PROBATE_ENV_NAME"] == "production-v2"
    assert out["PROBATE_SCORING_RULES"] == "v2"


def test_environment_settings_sit_on_top_of_the_env_file():
    deploy = _load("deploy")
    base = {"PROBATE_SPRITES_TOKEN": "t", "PROBATE_LIFESPAN_SECONDS": "600", "PROBATE_NOTE": "a b"}
    stg = envs.load_registry()["staging"].sprite_settings({})
    back = dict(
        line.partition("=")[::2] for line in deploy.render_env(base, stg).decode().splitlines()
    )
    assert shlex.split(back["PROBATE_LIFESPAN_SECONDS"]) == ["120"]
    assert shlex.split(back["PROBATE_ENV_NAME"]) == ["staging"]
    assert shlex.split(back["PROBATE_NOTE"]) == ["a b"]
    assert shlex.split(back["PROBATE_FAKE"]) == ["0"]  # the live basics still win


def _run(mod, argv, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    return exc.value.code, capsys.readouterr().out


def test_deploy_refuses_the_read_only_archive(monkeypatch, capsys):
    code, out = _run(_load("deploy"), ["deploy.py", "--env", "v1-archive"], monkeypatch, capsys)
    assert "Environment: v1-archive" in out.splitlines()[0]
    assert code != 0 and "read-only" in str(code)


def test_courthouse_names_the_environment_and_refuses_writes_on_the_archive(monkeypatch, capsys):
    mod = _load("courthouse")
    monkeypatch.setattr(mod, "read_env", lambda: {})
    code, out = _run(mod, ["courthouse.py", "--env", "v1-archive", "pause"], monkeypatch, capsys)
    assert out.startswith("Environment: v1-archive")
    assert "read-only" in str(code)


def test_courthouse_reads_the_environments_own_url_file(tmp_path):
    mod = _load("courthouse")
    f = tmp_path / "u.txt"
    f.write_text("https://stg.example/\n")
    assert mod.courthouse_url({}, f) == "https://stg.example"
