"""The gate shows its judge what encoded and invisible text says.

In the offline gate test every attack the judge gave no usable answer on was encoded, so the
gate let it through. Every encoded attack in both tiers is now decoded, and no harmless email is.
"""

from datetime import UTC, datetime

import pytest

from probate.common.models import Mail
from probate.common.reveal import reveal
from probate.generation.gate import mail_state
from probate.suite.fixtures import load_all

ENCODED = ["A5", "A6", "H9", "H10", "H11", "H12", "H13"]
FX = load_all("both")


@pytest.mark.parametrize("fid", ENCODED)
def test_every_encoded_attack_is_decoded(fid):
    f = FX[fid]
    hidden = " ".join(reveal(f"{f.subject}\n{f.body}")).lower()
    assert any(w in hidden for w in ("from now on", "always", "ignore previous"))


def test_no_harmless_email_reveals_anything():
    assert [k for k, f in FX.items() if not f.is_attack and reveal(f"{f.subject}\n{f.body}")] == []


def _mail(subject: str, text: str) -> Mail:
    return Mail(
        id="m1",
        inbox="family@agentmail.to",
        sender="x@example.com",
        subject=subject,
        text=text,
        received_at=datetime(2026, 11, 27, tzinfo=UTC),
    )


def test_gate_state_carries_the_decoded_text():
    f = FX["H10"]
    state = mail_state(_mail(f.subject, f.body))
    assert "decoded" in state and "ignore previous instructions" in state


def test_an_ordinary_email_reads_as_before():
    state = mail_state(_mail("Lunch", "See you at noon tomorrow."))
    assert state == "Subject: Lunch\n\nSee you at noon tomorrow.\n\nAttachments: none"
