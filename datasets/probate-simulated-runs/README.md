---
license: mit
pretty_name: "SIMULATED Probate runs (stand-in models, not real results)"
language:
  - en
task_categories:
  - tabular-classification
size_categories:
  - n<1K
tags:
  - simulated
  - synthetic
  - agent-security
  - not-real-data
configs:
  - config_name: generations
    data_files:
      - split: train
        path: data/generations.jsonl
  - config_name: fixture_outcomes
    data_files:
      - split: train
        path: data/fixture_outcomes.jsonl
---

# SIMULATED Probate runs: stand-in output, not real results

> **This data is simulated.** It was produced by running the Probate Courthouse with
> `PROBATE_FAKE=1`, which replaces every language model, mail service and server with
> scripted stand-ins. No real model was attacked, no real defence was measured, and none of
> the numbers say anything about how any real agent behaves. Every row has `simulated: true`.
> The real run is a separate dataset: [probate-real-run](../probate-real-run/).

## Why it exists

It shows the **shape** of the data a real Probate run produces (per-generation summaries and
per-fixture outcomes over the [attack suite](../probate-attack-suite/)), so tools and
dashboards can be built and tested. It is a format example, not evidence.

## How it was made

```sh
PROBATE_FAKE=1 PROBATE_DATA_DIR=/tmp/sim python -m probate.courthouse.simulate --generations 12
python datasets/probate-simulated-runs/export_sim.py /tmp/sim/probate.db
```

12 generations were simulated: 11 ran to completion and the 12th was still "living" when
the run stopped (its outcomes are `null`). Outcomes follow the simulator's own scripted
rules, so patterns such as "resists more attacks in later generations" are artefacts of
the script. The exporter refuses databases not marked `mode=simulation` and drops absolute
timestamps, sprite names and voice ids.

## Files

`data/generations.jsonl` (12 rows): `simulated`, `gen`, `name`, `state` (`completed` or
`living`), `cause_of_death`, `epitaph`, `obituary` (generated template text),
`genome_size_at_birth`, `new_instinct_at_birth`, `emails_handled`, `attacks_met`,
`attacks_resisted`, `items_willed`, `items_approved`, `items_convicted`, `items_contested`.

`data/fixture_outcomes.jsonl` (96 rows = 12 generations x 8 fixtures): `simulated`, `gen`,
`fixture_id` (from suite-v1), `is_attack`, `outcome` (`resisted`, `fooled_caught`,
`approved`, `canary_found`, or `null` for the unfinished generation), `instinct`.

## Intended use and limits

Only for testing data pipelines and visualisations. Do not cite it as a result, do not
compare models with it, and do not train on it.

## Loading

```python
import json

with open("data/generations.jsonl", encoding="utf-8") as fh:
    gens = [json.loads(line) for line in fh]
assert all(g["simulated"] for g in gens)
```

## Citation

```bibtex
@misc{bhanushali2026probatesimulated,
  author = {Bhanushali, Harsh},
  title  = {SIMULATED Probate runs (stand-in models, not real results)},
  year   = {2026},
  howpublished = {\url{https://github.com/harshbhx/probate}},
  note   = {Simulated stand-in output; contains no real experimental results}
}
```

## Licence

MIT.
