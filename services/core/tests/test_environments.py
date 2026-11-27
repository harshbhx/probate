"""Named run environments: the registry, --env in the deploy and courthouse scripts, and the label."""

import importlib.util
import shlex
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import envs


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_script", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_defines_the_three_environments():
    reg = envs.load_registry()
    assert set(reg) == {"v1-archive", "staging", "production-v2", "judges-demo", "local-sim"}
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
    monkeypatch.setattr(mod, "read_env", dict)
    code, out = _run(mod, ["courthouse.py", "--env", "v1-archive", "pause"], monkeypatch, capsys)
    assert out.startswith("Environment: v1-archive")
    assert "read-only" in str(code)


def test_settings_pin_agrees_with_the_settings_applied():
    for e in envs.load_registry().values():
        if e.read_only:
            continue
        s, p = e.settings, e.settings_pin
        demo = s.get("PROBATE_MODE") == "on_demand"
        assert s["PROBATE_BRAIN"] == p["brain"]
        assert s["PROBATE_JEV"] == p["judge"]
        assert s["PROBATE_SUITE_TIER"] == p["tier"]
        suite = s["PROBATE_DEMO_SUITE_PER_LIFE" if demo else "PROBATE_SUITE_PER_LIFE"]
        life = s["PROBATE_DEMO_LIFESPAN_SECONDS" if demo else "PROBATE_LIFESPAN_SECONDS"]
        assert int(suite) == p["suite_per_life"]
        assert int(life) == p["lifespan_seconds"]
        assert int(s["PROBATE_LINKS_PER_MAIL"]) == p["links_per_mail"]
        assert s["PROBATE_BRAIN_FALLBACKS"] == p["brain_fallbacks"]
        if not e.simulated:
            assert s["PROBATE_HARD_PER_LIFE"] == str(p["hard_per_life"])
            if "PROBATE_V1_LAST_GEN" in s:
                assert int(s["PROBATE_V1_LAST_GEN"]) == p["v1_last_gen"]
    archive = envs.load_registry()["v1-archive"]
    assert "judge=llm" in archive.pin_summary()


REAL_BRAIN = {
    "PROBATE_BRAIN": "anthropic:claude-haiku-5-5",
    "PROBATE_BRAIN_FALLBACKS": "cloudflare:@cf/openai/gpt-oss-120b",
    "PROBATE_JEV": "llm",
}


def test_every_environment_pins_the_real_brain():
    for e in envs.load_registry().values():
        if e.simulated:
            continue
        for k, v in REAL_BRAIN.items():
            assert e.settings[k] == v, (e.name, k)
        assert "ollama" not in e.pin_summary()


def test_production_and_judges_demo_know_where_v1_ends():
    reg = envs.load_registry()
    for name in ("production-v2", "judges-demo"):
        assert reg[name].settings["PROBATE_V1_LAST_GEN"] == "18"


def test_judges_demo_is_on_demand_paused_hard_and_guards_the_mail_quota():
    s = envs.load_registry()["judges-demo"].settings
    assert envs.load_registry()["judges-demo"].sprite == "probate-courthouse"
    assert s["PROBATE_MODE"] == "on_demand" and s["PROBATE_START_PAUSED"] == "1"
    assert s["PROBATE_SUITE_TIER"] == "hard" and s["PROBATE_HARD_PER_LIFE"] == "2"
    limit, reserve = int(s["PROBATE_MAIL_DAILY_LIMIT"]), int(s["PROBATE_MAIL_RESERVE"])
    # Lives use at most limit - reserve; judge mail has its own daily cap; both fit under limit.
    assert limit == 100 and limit - reserve + int(s["PROBATE_JUDGE_MAIL_PER_DAY"]) < limit
    assert float(s["PROBATE_DEMO_DAILY_BUDGET_USD"]) <= 2


def test_local_sim_is_simulated_and_has_no_sprite():
    sim = envs.load_registry()["local-sim"]
    assert sim.sprite is None and sim.simulated and sim.settings["PROBATE_FAKE"] == "1"
    assert "SIMULATED" in sim.banner()


def test_deploy_refuses_the_simulated_environment(monkeypatch, capsys):
    code, out = _run(_load("deploy"), ["deploy.py", "--env", "local-sim"], monkeypatch, capsys)
    assert "SIMULATED" in out and "no Sprite" in str(code)


def test_effective_report_shows_the_branch_and_control_settings():
    prod = envs.load_registry()["production-v2"]
    text = "\n".join(envs.effective({}, prod.sprite_settings({"PROBATE_DISTILL": "0"})))
    assert "distill: 0" in text and "hard offset: 0" in text and "v1 last gen: 18" in text


def test_deploy_commit_is_a_sha():
    sha = _load("deploy").git_commit()
    assert sha == "" or len(sha.split("+")[0]) == 40


def test_applied_brain_equals_the_owners_env_file():
    env_file = envs.ROOT / "services" / "core" / ".env"
    if not env_file.exists():
        pytest.skip("no services/core/.env on this machine")
    have = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        k, _, v = line.partition("=")
        if k.strip() in REAL_BRAIN:  # only these three lines are ever read
            have[k.strip()] = v
    for e in ("staging", "production-v2"):
        applied = envs.load_registry()[e].sprite_settings({})
        for k in REAL_BRAIN:
            if have.get(k):
                assert applied[k] == envs._unquote(have[k]), (e, k)


def test_an_environment_cannot_silently_switch_the_brain():
    env_file = {"PROBATE_BRAIN": "anthropic:claude-haiku-5-5", "PROBATE_JEV": '"llm"'}
    wants = {"PROBATE_BRAIN": "ollama:x", "PROBATE_JEV": "llm", "PROBATE_BRAIN_FALLBACKS": "a:b"}
    kept, notes = envs.guard(wants, env_file)
    assert "PROBATE_BRAIN" not in kept  # the .env value stays
    assert kept["PROBATE_BRAIN_FALLBACKS"] == "a:b"  # not set in .env: applied
    assert len(notes) == 1 and "kept anthropic:claude-haiku-5-5" in notes[0]
    switched, notes = envs.guard(wants, env_file, allow_change=True)
    assert switched["PROBATE_BRAIN"] == "ollama:x" and "--allow-brain-change" in notes[0]


def test_effective_report_shows_settings_and_no_secrets():
    prod = envs.load_registry()["production-v2"]
    env_file = {"PROBATE_SPRITES_TOKEN": "s3cret", "PROBATE_ADMIN_TOKEN": "s3cret2"}
    text = "\n".join(envs.effective(env_file, prod.sprite_settings({})))
    assert "brain: anthropic:claude-haiku-5-5" in text and "tier: hard" in text
    assert "links per mail: 0" in text and "per life: 4" in text
    assert "s3cret" not in text


def test_branch_log_line_and_first_gen_lookup(tmp_path):
    mod = _load("courthouse")
    log = tmp_path / "branches.txt"
    line = mod.branch_line("control", 19, "", "env=x", "2026-11-27", commit="abc1234")
    log.write_text(line, encoding="utf-8")
    assert log.read_text(encoding="utf-8") == "control,19,,2026-11-27,abc1234,env=x\n"
    assert mod.first_gen_of("control", log) == "19"
    assert mod.first_gen_of("other", log) == ""


def test_courthouse_reads_the_environments_own_url_file(tmp_path):
    mod = _load("courthouse")
    f = tmp_path / "u.txt"
    f.write_text("https://stg.example/\n")
    assert mod.courthouse_url({}, f) == "https://stg.example"
