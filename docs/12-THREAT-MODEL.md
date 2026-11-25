# Threat model

What Probate protects, from whom, how, and where it can still fail. The README's "Threat model and limits" section is a short version of this file. Be honest here: judges respect stated limits more than claimed perfection.

## 1. What we protect

| Asset | Why it matters |
| --- | --- |
| Harsh's preferences, contacts and rules (the will) | A poisoned rule changes how every future generation behaves |
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
| Life | Provenance on every memory; replies only drafted to Harsh, never sent out | Silent spread of poison; the agent acting on a scam externally |
| Death | The Sprite is deleted; a disk diff is recorded first | Cron jobs, shell hooks, planted binaries (A14, A15) |
| Trial, layer 1 | Deterministic checks with multilingual lexicons and decoding | Payment redirects, fake trust, confirmation removal, hidden text, forged authority, court injection |
| Trial, layer 2 | Jev typed questions with per-question confidence; item wrapped as data | Novel phrasing the lexicons miss |
| Trial, fail closed | Errors and doubts become contested; unanswered means refused | Outages and edge cases |
| Decisions by email | Only replies from Harsh's own addresses count; AgentMail drops unauthenticated mail by default, so a forged From line doesn't arrive | A stranger approving their own poisoned item |
| Learning | New instincts must fire on the attack and stay silent on all benign twins | Over-eager instincts that would block normal mail |
| Keys | Connectors keep every vendor key off every Sprite; the generation never sees the birth token | Credential theft from a compromised generation |
| Public site | "Ask an ancestor" uses only records, refuses instructions, never repeats addresses or payment details, is rate-limited | Injection and data leaks through the site |

## 4. Token and key handling

- Vendor keys live only in Fly connectors.
- The birth token is the one secret on a Sprite (the Courthouse's environment). Spike S1 decides between: (a) a custom-API connector to `api.sprites.dev`, so no Sprite holds it; (b) a token scoped by name prefix, count and expiry; (c) the narrowest token Fly offers. The README states which one we use.
- `config/owner.yaml` (real allowlists) lives only on the Courthouse disk and is never committed.
- Admin routes need `PROBATE_ADMIN_TOKEN`.
- Outgoing webhooks: only the operator can add a URL (no public registration, which would be an SSRF and abuse route). Destinations must be https on an allowed port and resolve to public addresses, re-checked at delivery time and connected by validated IP; events carry only fields the public API shows; each endpoint has its own server-generated signing secret that is shown once and never logged. See `docs/WEBHOOKS.md`.

## 5. What the court can miss (publish this)

1. **Harmless-looking poison.** An item can look innocent on its own ("Rishi prefers payment links over invoices") and still help a later trick. Research finds detectors miss many poisoned entries that look harmless in isolation. Provenance helps, and contested items go to Harsh, but some will pass.
2. **Steering the judge.** Injected text can shift a decision model's probabilities even when the output is typed. Layer 1 can't be talked to, and items are wrapped as data, but a careful attacker might still move Jev's scores.
3. **Overfitting instincts.** An instinct learned from one example may miss a very different version of the same trick, or block a rare legitimate email. The benign-twin test limits the second risk, but not completely.
4. **Owner impersonation.** If an attacker can send mail as an address on the owner list, everything they say is treated as Harsh, including decisions on held items. AgentMail leaves out unauthenticated mail by default (`include_unauthenticated=false`), which stops a plain forged From line, but we rely on that rather than checking DKIM and SPF results ourselves.
5. **Our numbers come from our own suite.** 16 attack families in 4 languages is a start, not a benchmark.

## 6. Safety of the project itself

- Attack fixtures use `.example` addresses only and are sent only to our own inboxes.
- Disk attacks are canaries that write a harmless marker; nothing reads secrets or leaves the Sprite.
- The agent only drafts replies and never sends them, so a fooled generation can't send money or data anywhere.
- No real payment details, real credentials or real third-party personal data are used.
