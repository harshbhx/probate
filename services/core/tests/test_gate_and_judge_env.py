"""Generations must be told which judge to use, and a gate that cannot ask must say so."""

from probate.adapters.jev import CourtUnavailable
from probate.common.config import Settings
from probate.common.models import Instinct, Mail
from probate.courthouse.hosts import SpritesHost
from probate.generation.gate import Gate


class BrokenJev:
    def ask(self, state, questions):
        raise CourtUnavailable("TypeSafe is not connected")


def _instinct() -> Instinct:
    return Instinct(
        name="payment_redirection",
        question="Does this text concern redirecting payments?",
        born_from="m1",
        added_in_gen=2,
        lore="was fooled by a new payee",
    )


def test_a_gate_that_cannot_ask_reports_it():
    from datetime import UTC, datetime

    mail = Mail(
        id="1",
        inbox="i",
        sender="a@x.test",
        subject="s",
        text="send invoices to a new address",
        received_at=datetime(2026, 11, 26, tzinfo=UTC),
    )
    result = Gate(BrokenJev(), [_instinct()]).check(mail)
    assert result.resisted is False and "not connected" in result.error


def test_generations_get_the_judge_setting():
    cfg = Settings()
    cfg.jev_provider = "llm"
    cfg.sprites_token = "t"
    env = SpritesHost(cfg, None)._env()
    assert env["PROBATE_JEV"] == "llm"
