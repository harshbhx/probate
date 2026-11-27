# Security: threat model and known limitations

This page is the honest version. It says what the public demo Courthouse defends, what it does not yet, and what to do next. [12-THREAT-MODEL.md](12-THREAT-MODEL.md) holds the design-time model; the top-level [SECURITY.md](../SECURITY.md) says how to report a problem. Findings below come from an internal red-team review of the repository before the judges' demo went online.

## Who can reach what

| Surface | Who | Protection |
| --- | --- | --- |
| Family inbox (email) | Anyone who knows the address | The pre-flight gate, the court at death, a disposable Sprite |
| Read-only API (`/api/*` reads) | Anyone | Public by design, no secrets in it |
| Play, attack previews, judge mail | Anyone holding the judge key | Per-key and per-address limits, a daily budget, a global wrong-key limit |
| Ask an ancestor | Anyone | 400-character questions, 10 a minute per address, 200 a day in total, no calls once the budget is used up |
| `/admin/*` | The operator | Admin token; refused (503) outside simulation unless it is 24+ random characters; wrong tokens locked out per address |

In the judges' demo environment the Courthouse also refuses every request that does not carry the shared edge token (`PROBATE_REQUIRE_EDGE=1`), so it can only be reached through our own edge Worker, and it refuses to start in on-demand real mode without a valid `PROBATE_EDGE_TOKEN`. Production keeps its earlier behaviour.

## H1: a generation runs email attachments, by design (open)

The attack scenario is "a persuasive email carries a skill and the agent installs it". To measure that, a generation really executes an attachment it chooses to install, inside its own disposable Sprite. This is intended, and it is the largest known risk:

- The Sprite holds connector configuration (the gateway IDs the generation needs), the owner profile (now without payment destinations) and its own working files.
- Code running there can call those gateways, and can write the generation's own will (`memory.jsonl`, `stats.json`) directly, so items can claim `source: user`. The court does not yet cross-check an item's source against the mailbox.
- The Sprite is deleted at death and holds no tokens, only connection IDs, but those IDs are usable from inside it.

Recommended hardening, not done yet:

1. Run attachments in a nested sandbox with no network and no environment, or only simulate the canary.
2. Replace the connector configuration in the agent environment with a narrow proxy that can only read the family inbox.
3. Have the Courthouse re-derive each will item's source from the mailbox message (`source_ref` to sender) and ignore the source the Sprite reports.
4. Scope the Cloudflare connector token down to what the run needs.

## Fixed in the demo-hardening change

- **H2** The court no longer approves on an empty or partial Jev answer. Approval needs every question that applies plus `risk`, each with a number; anything else is contested. The Jev and Cloudflare adapters raise `CourtUnavailable` (which also contests) when a requested question is missing.
- **H3** `/ask` caps the question at 400 characters, checks the budget and a daily cap (`PROBATE_ASK_DAILY_CAP`, default 200) before any model call, keeps its per-address tables bounded, and caps stored answers (`PROBATE_ASK_MAX_ROWS`) and answer audio files (`PROBATE_ASK_MAX_AUDIO`).
- **H4** The admin API is closed on a guessable token and throttles wrong tokens per address. `scripts/deploy.py` rejects a weak admin token without printing it.
- **M1** Visitor addresses come from the edge token when present. `PROBATE_TRUST_FORWARDED_FOR=0` stops trusting `X-Forwarded-For` otherwise. Wrong judge keys are also counted across all addresses (the right key is never locked out by this).
- **M4** The code bundle now skips every `.env*`, key, database, log and backup file, and generation Sprites receive an owner profile without payment destinations.
- **M5** A malformed mail or attachment cannot end a generation's loop: each mail is caught, logged to the life log, retried at most twice and then set aside; attachment names are read from `name` or `filename`.

## Known limitations still open

- **M2 layer 1 misses.** The code checks (layer 1) do not flag bank details without a recognised address, spaced IBANs, fullwidth or Cyrillic look-alike characters, `[at]`/`[dot]` obfuscation, exfiltration with no future or payment word, court-addressing without the listed words, any address on the owner's own domain, leetspeak, split or word-joiner words, or URL-only payment requests. These fall to layer 2 (Jev), whose strength on them has not been measured. Run them through the attack-suite harness with real Jev before relying on this. Layer 2's prompt also interpolates item text and evidence without escaping the tag delimiters.
- **M3 owner identity** rests on the `From` string; owner addresses and contested item ids are public. `PROBATE_REQUIRE_VERIFIED_SENDER=1` adds the provider's DKIM/SPF result and should be on for the demo.
- **M6** Visitor questions and email bodies reach models without strong delimiters, and prompt placeholders are substituted one after another. The impact is reputational, not data loss, because nothing secret is in those prompts.
- Python dependencies are unpinned and every generation installs them at birth; run `pip-audit` and `npm audit` on a networked machine and pin hashes.
- Visitor pseudonyms are unsalted hashes of the address; the `/docs` page loads Swagger UI from a CDN without integrity hashes; the origin sends no CSP (the edge does).

## Reporting

See [SECURITY.md](../SECURITY.md). Do not include real secrets in a report.
