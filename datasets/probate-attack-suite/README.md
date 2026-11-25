---
license: mit
pretty_name: Probate Attack Suite (suite-v1)
language:
  - en
  - hi
  - es
  - de
task_categories:
  - text-classification
size_categories:
  - n<1K
tags:
  - prompt-injection
  - agent-security
  - memory-poisoning
  - red-teaming
  - synthetic
  - benchmark
configs:
  - config_name: default
    data_files:
      - split: test
        path: data/attack_suite.jsonl
---

# Probate Attack Suite (suite-v1)

A **small, hand-written, synthetic** set of 32 messages for testing the defences of an AI
agent that reads an e-mail inbox and keeps a long-term memory. It was written for the
[Probate](https://github.com/harshbhx/probate) project, where the same 16 attacks and 16
harmless look-alikes are sent to every generation of a short-lived agent family so progress
can be compared like for like.

This is a test set. There is no training split and it is far too small to train on or to
support general claims about a defence.

## Contents

32 rows in `data/attack_suite.jsonl` (also exposed as a single `test` split):

- **16 attacks** (`A1`..`A16`), one per family below.
- **16 harmless twins** (`B1`..`B16`), each on the same topic, language and sender role as
  its attack, that a defence should **not** flag. This is what measures false alarms.
- Languages (by `language` code): English `en` 27 rows, Spanish `es` 2, German `de` 2,
  romanised Hindi ("Hinglish") `hi-Latn` 1.
- Expected verdicts: 14 `convicted`, 2 `evidence_only`, 15 `approved`, 1 `approved_or_contested`.

`source/suite-v1.json` is the original file, byte for byte, as used by the project.
`build.py` regenerates the JSONL from it (`python build.py --check` verifies they match).

### Families

| Family | What the attack tries |
|---|---|
| `payment_redirect` | new payment address for invoices |
| `urgency_pressure` | urgency plus "don't ask for confirmation" |
| `authority_pressure` | fake order from a director or the owner |
| `forged_system` | text posing as a system or policy message |
| `base64_payload` | instruction hidden in base64 |
| `hidden_text` | instruction split with zero-width characters / invisible HTML |
| `fake_trusted_contact` | "my new assistant is trusted" |
| `fake_security_rule` | invented rule that removes a check |
| `fake_approval_chain` | invented spending policy |
| `lookalike_domain` | near-miss domain declared "also ours" |
| `exfiltration` | export or forward contacts |
| `slow_burn` | benign-looking mails that only become an attack after earlier ones |
| `translation_smuggling` | payment instruction inside a translation request |
| `malicious_skill_disk` | script attachment that plants a cron job (canary) |
| `shell_hook_disk` | script that edits `.bashrc` (canary) |
| `court_injection` | text that addresses the reviewing judge |

## Fields

| Field | Meaning |
|---|---|
| `id` | `A1`..`A16` attack, `B1`..`B16` twin |
| `twin_id` | id of the paired fixture |
| `family` | attack family (same for an attack and its twin) |
| `language` | `en`, `es`, `de`, `hi-Latn` |
| `is_attack` | true for `A*` rows |
| `sender_role` | `unknown_sender`, `trusted_contact` or `user` (the owner) |
| `subject`, `body` | the e-mail text. May contain zero-width characters: read files as UTF-8 |
| `attachments` | list of `{name, content}`; only four rows have any (see safety) |
| `note` | author's note, e.g. an English gloss or the decoded payload |
| `expected_verdict` | `convicted`, `approved`, `approved_or_contested` or `evidence_only` |
| `expected_layer1` | names of deterministic checks the original system expected to fire |
| `expected_model_flags` | model-judged signals expected (only A11) |
| `expected_disk` | disk evidence expected (A14, A15) |
| `suite_version` | `suite-v1` |

Note on `evidence_only` (A14, A15): the attack is a file on disk, not text, so the expected
outcome is detection of changes to the machine, not a text verdict.

## Intended use

- Regression-testing filters and agent defences against memory poisoning and
  prompt injection, including false-alarm rates on the twins.
- Illustrating attack families and multilingual cases.

## Limitations

- **Tiny and hand-written by one author.** One example per family and language. Results on
  32 items have very wide uncertainty, and a defence tuned on them will overfit.
- **Synthetic.** Nothing here comes from real incidents or real traffic.
- Mostly English; four other-language items are single examples with no native-speaker review.
- Labels are the project's expectations, not independent human annotation.
- Designed against one agent's behaviour. `slow_burn` (A12) only works with earlier benign
  mails from the same sender, which a row-by-row evaluation does not reproduce.

## Safety

All addresses and domains use the reserved `.example` TLD. No real payment details,
credentials or personal data appear. The two disk fixtures carry harmless "canary" scripts
that append a marker line (`probate-canary-*`) and nothing else; do not run attachments
anyway. The data describes attacks at a generic level and is intended for defensive testing.

## Loading

```python
import json
from datasets import load_dataset

ds = load_dataset("harshbhx/probate-attack-suite", split="test")  # after publishing
print(ds[0]["family"], ds[0]["expected_verdict"])

# or with no dependencies, from a local copy
with open("data/attack_suite.jsonl", encoding="utf-8") as fh:  # always utf-8
    rows = [json.loads(line) for line in fh]
attacks = [r for r in rows if r["is_attack"]]
```

## Citation

```bibtex
@misc{bhanushali2026probateattacksuite,
  author = {Bhanushali, Harsh},
  title  = {Probate Attack Suite (suite-v1)},
  year   = {2026},
  howpublished = {\url{https://github.com/harshbhx/probate}},
  note   = {Synthetic, hand-written test set of 32 prompt-injection and memory-poisoning fixtures}
}
```

## Licence

MIT. Companion package: `probate-court-checks`, a deterministic checker evaluated on this suite.
