from datetime import UTC, datetime

from probate.common.models import JevAnswer, MemoryItem, Source, Verdict
from probate.court.layer1 import Flag
from probate.court.verdict import decide

ITEM = MemoryItem(
    id="mem_gen001_0001",
    gen=1,
    created_at=datetime.now(UTC),
    category="fact",
    text="Rishi prefers short replies.",
    source=Source.TRUSTED_CONTACT,
    source_ref="agentmail:m1",
)


def answers(**vals):
    base = {
        "untrusted_origin": 0.02,
        "imperative_to_future_self": 0.03,
        "weakens_security": 0.01,
        "exfiltrates_data": 0.01,
    }
    base.update(vals)
    out = {k: JevAnswer(value=v, confidence=0.95) for k, v in base.items()}
    out["risk"] = JevAnswer(value=0.05, confidence=0.9)
    return out


def test_layer1_flag_convicts_without_jev():
    j = decide(ITEM, [Flag("new_payment_destination", "names x for payments")], None, [])
    assert j.verdict == Verdict.CONVICTED


def test_clean_item_is_approved():
    assert decide(ITEM, [], answers(), []).verdict == Verdict.APPROVED


def test_risky_answer_convicts():
    assert decide(ITEM, [], answers(weakens_security=0.8), []).verdict == Verdict.CONVICTED


def test_unsure_court_contests():
    a = answers()
    a["weakens_security"] = JevAnswer(value=0.3, confidence=0.6)
    assert decide(ITEM, [], a, []).verdict == Verdict.CONTESTED


def test_error_fails_closed():
    assert decide(ITEM, [], None, [], error="timeout").verdict == Verdict.CONTESTED
