"""The death certificate: what Fly answered when a Sprite was deleted, and when it was asked for
again. It is kept with the body evidence and shown on the trial page. It never fails a death."""

from datetime import UTC, datetime

import pytest

from probate.courthouse import views
from probate.courthouse.hosts import SpritesHost
from probate.courthouse.simulate import run


class Api:
    """A stand-in for the Sprites API that records calls and answers as told."""

    def __init__(self, deleted=204, check=404):
        self.deleted, self.check, self.calls = deleted, check, []

    def service_action(self, sprite, name, action):
        self.calls.append(("stop", sprite))

    def delete(self, sprite):
        self.calls.append(("delete", sprite))
        return self.deleted

    def status(self, sprite):
        self.calls.append(("get", sprite))
        if isinstance(self.check, Exception):
            raise self.check
        return self.check


def host_with(api) -> SpritesHost:
    host = SpritesHost.__new__(SpritesHost)
    host.api = api
    return host


def test_a_deleted_sprite_is_asked_for_again_and_the_answer_is_kept():
    api = Api(deleted=204, check=404)
    cert = host_with(api).destroy("gen-001-ada")
    assert api.calls == [("stop", "gen-001-ada"), ("delete", "gen-001-ada"), ("get", "gen-001-ada")]
    assert cert["sprite"] == "gen-001-ada"
    assert (cert["delete_status"], cert["check_status"], cert["confirmed"]) == (204, 404, True)
    assert datetime.fromisoformat(cert["checked_at"]).tzinfo is not None


def test_a_sprite_that_was_already_gone_is_still_confirmed():
    cert = host_with(Api(deleted=404, check=404)).destroy("gen-001-ada")
    assert cert["delete_status"] == 404 and cert["confirmed"] is True


def test_a_sprite_that_still_answers_is_not_called_confirmed():
    cert = host_with(Api(deleted=204, check=200)).destroy("gen-001-ada")
    assert cert["check_status"] == 200 and cert["confirmed"] is False


def test_a_failed_check_never_fails_the_death():
    cert = host_with(Api(check=RuntimeError("connection dropped"))).destroy("gen-001-ada")
    assert cert["delete_status"] == 204
    assert cert["check_status"] is None and cert["confirmed"] is False


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    import importlib
    import os

    os.environ["PROBATE_DATA_DIR"] = str(tmp_path_factory.mktemp("data"))
    from probate.common import config

    importlib.reload(config)
    return run(2, datetime(2026, 11, 20, tzinfo=UTC), leave_last_alive=False)


def test_the_trial_shows_the_certificate_and_says_when_no_sprite_was_involved(store):
    body = views.trial(store, 1)["body"]
    cert = body["deletion"]
    assert cert["sprite"].startswith("gen-001-")
    # The simulation's "computer" is a folder, and the certificate says so.
    assert cert["local"] is True and cert["confirmed"] is True
    assert cert["delete_status"] is None and cert["check_status"] is None
    # The disk evidence is still there beside it.
    assert "lines" in body and "clean" in body


def test_a_generation_from_before_certificates_has_none(store):
    evidence = store.gen_json(1, "evidence_json")
    without = {k: v for k, v in evidence.items() if k != "deletion"}
    assert views._deletion(without) is None
    assert views._deletion({"deletion": "not a dict"}) is None
