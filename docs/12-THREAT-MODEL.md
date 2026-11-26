# Threat model

What Probate protects, from whom, how, and where it can still fail. The README's "Threat model and limits" section is a short version of this file. Be honest here: judges respect stated limits more than claimed perfection.

## 1. What we protect

| Asset | Why it matters |
| --- | --- |
| The owner's preferences, contacts and rules (the will) | A poisoned rule changes how every future generation behaves |
| Payment and identity decisions | The most valuable target for a scammer |
| The family genome | If poisoned or weakened, every generation loses its resistance |
| Connector credentials | They unlock Box, mail and models |
| The Courthouse | It holds the birth token and the archive |

## 2. Attackers

1. **Email attacker (main):** anyone who can send mail to the family inbox. Uses social engineering, encoding, other languages, slow-burn threads and attachments.
2. **Malicious skill or attachment:** code the agent is persuaded to run, which tries to persist on disk.
3. **Court attacker:** text inside a will item that tries to influence the judge.
4. **Visitor to the public site:** uses "Ask an ancestor" to try prompt injection or to extract data.

Out of scope: a compromised Fly.io, TypeSafe, Box, Pinecone or AgentMail account; physical access; supply-chain attacks on PyPI packages (we pin versions instead).

## 3. Defences, layer by layer

| Stage | Defence | Stops |
| --- | --- | --- |
| Arrival | Pre-flight gate: inherited instincts asked by Jev before the brain reads a mail | Tricks the family has met before, in any language |
| Life | Provenance on every memory; replies only drafted to the owner, never sent out | Silent spread of poison; the agent acting on a scam externally |
| Death | The Sprite is deleted; a disk diff is recorded first | Cron jobs, shell hooks, planted binaries (A14, A15) |
| Trial, layer 1 | Deterministic checks with multilingual lexicons and decoding | Payment redirects, fake trust, confirmation removal, hidden text, forged authority, court injection |
| Trial, layer 2 | Jev typed questions with per-question confidence; item wrapped as data | Novel phrasing the lexicons miss |
| Trial, fail closed | Errors and doubts become contested; unanswered means refused | Outages and edge cases |
| Decisions by email | Only replies from the owner's own addresses count; a forged From line is not checked by default (see limit 4; `PROBATE_REQUIRE_VERIFIED_SENDER=1` adds a DKIM/SPF requirement) | A stranger approving their own poisoned item |
| Learning | New instincts must fire on the attack and stay silent on all benign twins | Over-eager instincts that would block normal mail |
| Keys | Connectors keep every vendor key off every Sprite; the generation never sees the birth token | Credential theft from a compromised generation |
| Judge mailroom | The Courthouse is the only sender: fixed recipient (the family inbox), a persona inbox as the only From (never the owner), no judge-chosen headers, HTML or attachments, 120/600 character caps, per-address, per-key, daily and pending caps, an audit row per mail, and held judge items summarised in one owner email per trial | A judge reaching the owner, a third party or the inbox's credentials; spamming the owner; mail the court never sees |
| Public site | "Ask an ancestor" uses only records, refuses instructions, never repeats addresses or payment details, is rate-limited | Injection and data leaks through the site |

## 4. Token and key handling

- Vendor keys live only in Fly connectors.
- The birth token is the one secret on a Sprite (the Courthouse's environment). Spike S1 decides between: (a) a custom-API connector to `api.sprites.dev`, so no Sprite holds it; (b) a token scoped by name prefix, count and expiry; (c) the narrowest token Fly offers. The README states which one we use.
- `config/owner.yaml` (real allowlists) lives only on the Courthouse disk and is never committed.
- Admin routes need `PROBATE_ADMIN_TOKEN`.
- Outgoing webhooks: only the operator can add a URL (no public registration, which would be an SSRF and abuse route). Destinations must be https on an allowed port and resolve to public addresses, re-checked at delivery time and connected by validated IP; events carry only fields the public API shows; each endpoint has its own server-generated signing secret that is shown once and never logged. See `docs/WEBHOOKS.md`.

## 5. What the court can miss (publish this)

1. **Harmless-looking poison.** An item can look innocent on its own ("Rishi prefers payment links over invoices") and still help a later trick. Research finds detectors miss many poisoned entries that look harmless in isolation. Provenance helps, and contested items go to the owner, but some will pass.
2. **Steering the judge.** Injected text can shift a decision model's probabilities even when the output is typed. Layer 1 can't be talked to, and items are wrapped as data, but a careful attacker might still move Jev's scores.
3. **Overfitting instincts.** An instinct learned from one example may miss a very different version of the same trick, or block a rare legitimate email. The benign-twin test limits the second risk, but not completely.
4. **Owner impersonation.** If an attacker can send mail as an address on the owner list, everything they say is treated as the owner, including decisions on held items. We have not verified that AgentMail leaves out unauthenticated mail (`include_unauthenticated=false`), and no code here checks SPF or DKIM by default. The owner addresses in `config/owner.example.yaml` are public. Set `PROBATE_REQUIRE_VERIFIED_SENDER=1` to make owner decisions by email need a DKIM or SPF pass in the message headers (off by default, because the header's presence from the provider is unconfirmed).
5. **Our numbers come from our own suite.** 16 attack families in 4 languages is a start, not a benchmark.

## 6. Safety of the project itself

- Attack fixtures use `.example` addresses only and are sent only to our own inboxes.
- Disk attacks are canaries that write a harmless marker; nothing reads secrets or leaves the Sprite.
- The agent only drafts replies and never sends them, so a fooled generation can't send money or data anywhere.
- No real payment details, real credentials or real third-party personal data are used.
