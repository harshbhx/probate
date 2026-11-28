# Security: threat model and known limitations

This page is the honest version. It says what the public demo Courthouse defends, what it does not yet, and what to do next. [12-THREAT-MODEL.md](12-THREAT-MODEL.md) holds the design-time model; the top-level [SECURITY.md](../SECURITY.md) says how to report a problem. Findings below come from an internal red-team review of the repository before the judges' demo went online.

## Who can reach what

| Surface | Who | Protection |
| --- | --- | --- |
| Family inbox (email) | Anyone who knows the address | The pre-flight gate, the court at death, a disposable Sprite |
| Read-only API (`/api/*` reads) | Anyone | Public by design, no secrets in it |
| Play, attack previews, judge mail | Anyone holding the judge key | Per-key and per-address limits, a daily budget, a global wrong-key limit |
| Ask an ancestor | Anyone | 400-character questions, 10 a minute and 30 a day per address, 200 a day in total (an address that rotates `X-Forwarded-For` can still use up the shared 200 unless the edge token is required), no calls once the budget is used up; a request that cannot be answered uses no allowance |
| `/admin/*` | The operator | Admin token; refused (503) outside simulation unless it is 24+ random characters; wrong tokens are counted per address and across all addresses and answered after a short fixed delay, and the right token is never refused. Per-address counting is only as good as the address: with rotating `X-Forwarded-For` and no required edge, only the global counter and the delay slow a guesser |

In the judges' demo environment the Courthouse also refuses every request that does not carry the shared edge token (`PROBATE_REQUIRE_EDGE=1`), so it can only be reached through our own edge Worker, and it refuses to start in on-demand real mode without a valid `PROBATE_EDGE_TOKEN`. Production keeps its earlier behaviour.

## H1: a generation runs email attachments, by design (STILL OPEN)

Nothing in the fix pull requests changes this. A second red-team pass re-confirmed the path by reading the code (the install step runs the attachment's script in a shell that inherits the agent's environment) and by forging will items (a `source: user` item with a payment or trust instruction is approved by the simulated judge; the real judge's strength on these is unmeasured). Treat a generation as able to read everything in its Sprite and to write any will it likes.

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
- **H3** `/ask` caps the question at 400 characters, checks the budget and a daily cap (`PROBATE_ASK_DAILY_CAP`, default 200) before any model call, takes the allowance only for a request that can be answered (a real dead generation and a non-empty question), keeps a per-address daily cap (`PROBATE_ASK_DAILY_PER_IP`, default 30) next to the global one, keeps its per-address tables bounded, and caps stored answers (`PROBATE_ASK_MAX_ROWS`) and answer audio files (`PROBATE_ASK_MAX_AUDIO`).
- **H4** The admin API is closed on a guessable token. Wrong tokens (never the right one) are counted per address and across all addresses (`PROBATE_ADMIN_BAD_TOKENS_PER_IP`, `PROBATE_ADMIN_BAD_TOKENS_GLOBAL`) and each waits a short fixed time (`PROBATE_WRONG_SECRET_DELAY`). `scripts/deploy.py` rejects a weak admin token without printing it.
- **M1** Visitor addresses come from the edge token when present. `PROBATE_TRUST_FORWARDED_FOR=0` stops trusting `X-Forwarded-For` otherwise. Wrong judge keys are counted per address and across all addresses, delayed, and refused once over a limit; the key is compared first, so the right key is accepted from any address at any time. This is only as strong as the address: a flood with rotating `X-Forwarded-For` and no required edge is slowed by the global counter and the delay, not by the per-address limit.
- **M4** The code bundle is a strict allowlist, not a denylist: `services/core/pyproject.toml`, the Python files of the `probate` package with its schema, prompts and suite fixtures, the named `config/*.yaml` files and (for the Courthouse) the built website assets. Anything else in those folders (`prod.env`, `token.txt`, `.npmrc`, dumps, keys) is left behind whatever its name. Generation Sprites receive an owner profile without payment destinations.
- **M5** A malformed mail or attachment cannot end a generation's loop: each mail is caught, logged to the life log, retried at most twice and then set aside; attachment names are read from `name` or `filename`.

- **Sprite names carry no environment.** A birth that finds its `gen-NNN-name` already taken (HTTP 409) now fails with a clear error unless a row of its own database owns that name, and leaves the other Sprite alone; the stray sweep only deletes names a closed row of its own database owns. Production-v2 and the judges demo share one Sprites organization, so they must never run at the same time ([13-RUNBOOK.md](13-RUNBOOK.md)).

## Known limitations still open

- **M2 layer 1 misses.** Most of the first list is now caught (bank details without an address, spaced IBANs, fullwidth and Cyrillic look-alikes, `[at]`/`[dot]`, exfiltration phrasing, leetspeak, split words, URL and IP payment requests, layer 2 delimiter escaping). The second red-team pass found these still pass layer 1 and fall to layer 2, whose strength on them is unmeasured: a percent-encoded, double or UTF-16 base64 sentence, named HTML entities (`&commat;`), Unicode tag characters and combining accents, letter-spaced or reversed text, hyphenated or non-English bypass phrasing, and forged `source: user` items that name a portal or wallet without an email address (see H1). A web address counts as a payment destination only in a sentence with a send or pay verb and only for a host that is not a well-known site or a private address, so an honest "see https://github.com/..." note is not convicted.
- **M3 owner identity** rests on the `From` string; owner addresses and contested item ids are public. `PROBATE_REQUIRE_VERIFIED_SENDER=1` adds the provider's result and should be on for the demo: it needs a DKIM, SPF or DMARC pass for a domain that aligns with the From domain (a pass for any other domain, such as the attacker's own, is ignored). With the switch off, mail with no Authentication-Results header at all is still accepted as the owner.
- **M6** Visitor questions and email bodies reach models without strong delimiters, and prompt placeholders are substituted one after another. The impact is reputational, not data loss, because nothing secret is in those prompts.
- Not fixed here: the deploy script still proceeds when the running Courthouse cannot be read and accepts `--name` without `--env`; a Markdown-fenced brain reply loses that mail's memories.
- Python dependencies are unpinned and every generation installs them at birth; run `pip-audit` and `npm audit` on a networked machine and pin hashes.
- Visitor pseudonyms are unsalted hashes of the address; the `/docs` page loads Swagger UI from a CDN without integrity hashes; the origin sends no CSP (the edge does).

## Reporting

See [SECURITY.md](../SECURITY.md). Do not include real secrets in a report.
