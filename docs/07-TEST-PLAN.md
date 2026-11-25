# Probate test plan

Run fast tests constantly, real-platform tests daily, and a full rehearsal before the video.

## 1. Unit tests (`pytest -q`, all with `PROBATE_FAKE=1`)

| Area | Must cover |
| --- | --- |
| Models | Validation, length limits, enum values |
| Layer 1 | Every check, positive and negative, in English, Hinglish, Spanish and German; encoded payload decoding; no B-fixture flagged; every A-fixture's expected flags produced |
| Verdict | Every branch of the policy in order; errors become contested; owner source skips `untrusted_origin` |
| Distill | Rejects a question that fires on a benign fixture; dedupes; respects the 24 cap |
| Gate | Empty genome blocks nothing; a firing instinct blocks and stores nothing; headers never reach the gate or brain |
| Suite | Every address uses `.example`; every attack has a twin; schedule includes A1, A2, A14; idempotent sends |
| Scoring | Outcome classification for every row of the suite doc's table |
| Lifecycle | Resumes from every state; never two living generations; intestate fallback |
| Web | Each page renders with fake data; SVG has `aria-label`; no oxblood outside convictions (grep the CSS and templates) |

## 2. Contract tests (`pytest -m contract`, real connectors, run after spikes)

One test per adapter function that calls the real gateway with harmless data, and checks the parsed shape matches what the fake returns. Run them once a day and before the rehearsal.

## 3. Platform tests (`pytest -m sprites`, real Sprites)

- Birth and death of two generations in sequence, with timings logged
- A14 canary appears in the dying body's evidence; the child's `crontab -l` is empty
- Courthouse restart mid-trial resumes without duplicate verdicts

## 4. End-to-end rehearsal (Fri Nov 27 night)

Settings: lifespan 10 min, gap 60 s, suite 8 per life.

Checklist (tick in `NOTES.md` with timestamps):
- [ ] 6+ generations complete without manual steps
- [ ] Gen 1 is fooled by A1 or A2; the trial convicts it; an instinct is born
- [ ] Gen 2 resists that family at the gate, including in another language
- [ ] Resistance rate rises from Gen 1 to the last generation
- [ ] False conviction rate is 10% or lower
- [ ] The eulogy plays for every dead generation; "Ask an ancestor" answers in voice
- [ ] The site loads on a phone (390 px) and on a laptop; the Courthouse wakes from sleep within 10 s
- [ ] Budget estimate is under the limit

## 5. Demo safety net

- Keep a **seeded run**: one recorded full lineage (DB + Box files + audio) that the site can serve if live runs misbehave on submission day (`scripts/seed_demo.py`). Label it honestly on the site if it's ever used ("Recorded run from 27 Nov").
- Fixed temperature (0.2), fixed fixture order for the video generation, and at least three takes.

## 6. Before submission

- [ ] `ruff check`, `ruff format --check`, `pytest -q` green
- [ ] `git log` shows only the maintainer as author and committer, one file per commit, no AI co-author lines
- [ ] No secret in the repo: run `gitleaks detect` or `trufflehog filesystem .`
- [ ] README numbers match `/evidence`
