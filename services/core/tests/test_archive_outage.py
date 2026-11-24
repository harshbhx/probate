"""A Box outage must not stall the family: trials still finish and the site still has them."""

from datetime import UTC, datetime

from probate.adapters.archive import LocalArchive
from probate.courthouse.simulate import run


def test_family_survives_archive_outage(tmp_path, monkeypatch):
    monkeypatch.setenv("PROBATE_DATA_DIR", str(tmp_path))

    def down(*_a, **_k):
        raise ConnectionError("Box is down")

    monkeypatch.setattr(LocalArchive, "put_text", down)
    monkeypatch.setattr(LocalArchive, "append_text", down)
    store = run(3, datetime(2026, 11, 20, tzinfo=UTC), leave_last_alive=False)

    assert [g.state for g in store.generations()] == ["tried", "tried", "tried"]
    assert store.get_setting("archive_missing:1") == "1"
