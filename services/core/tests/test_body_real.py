"""A real Sprite image may have no `crontab` program; the baseline must still work."""

import subprocess

from probate.generation.body import Body


def test_baseline_without_a_crontab_program(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "crontab")

    monkeypatch.setattr(subprocess, "run", missing)
    body = Body(tmp_path, real=True)
    assert body.crontab() == []
    baseline = body.baseline()
    assert baseline["crontab"] == []
    assert body.evidence(baseline)["crontab_added"] == []
