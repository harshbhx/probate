# Setup and verification spikes

Do this first, on Wed Nov 25. Harsh does the account and dashboard steps (only he can). Agent A writes and runs the spike scripts in `scripts/`. Record every finding in `docs/SPIKE-RESULTS.md` (endpoint shapes, timings, gotchas), but **never** keys or tokens.

## 1. Account (Harsh)

1. Sign up at https://fly.io/app/sign-up?s=hacksgiving.
2. Add a card. That unlocks the larger Sprites credit; without one, the credit is tiny and expires quickly. Check the current amount on the billing page and write it in `SPIKE-RESULTS.md`.
3. Install the CLIs: `flyctl`, and the `sprite` CLI if offered (see https://docs.sprites.dev). Run `sprite org auth`.

## 2. Connectors (Harsh, in the dashboard)

Fly dashboard → your org → **Sprites → Connectors → Add connector**. For each one: add the key or sign in, then under access turn **off** "Allow all sprites" and allow by name prefix: `courthouse` and `gen-`.

| Connector | Needs | Used for |
| --- | --- | --- |
| TypeSafeAI | TypeSafe API key | The court (layer 2), the gate, distillation tests |
| Box | Box sign-in (read and write) | The family archive in `/Probate/` |
| Pinecone | Pinecone API key; create index `probate-ancestry` | Ancestral memory |
| AgentMail | AgentMail API key | Family, friend-sim and stranger inboxes (three, the free plan) |
| Custom API `cloudflare` | Cloudflare API token with Email Sending permission, upstream `https://api.cloudflare.com` | Harsh's own test emails, from `harsh@dualmindlab.tech` |
| ElevenLabs | ElevenLabs API key | Eulogies and ancestor answers |
| Ollama Cloud | Ollama account key | The brain |
| Anthropic | Anthropic key (Claude for Startups credits) | Brain fallback and distillation |
| Custom API (optional) | Sprites API token | Lets the Courthouse create and delete Sprites without holding the key (try it in S1) |

After adding each one, open its detail page, copy the **API Usage** example and the connection ID into `SPIKE-RESULTS.md` (IDs only, no keys).

## 3. Spikes (Agent A, scripts in `scripts/`)

Much is already confirmed from vendor docs (see `docs/09-API-REFERENCE.md`): Sprites create/get/delete, exec query params, filesystem read/write, services API, URL privacy, the gateway URL pattern, Jev's request and answer shape, AgentMail send with custom headers, Pinecone records upsert, Ollama Cloud `/api/chat`. The spikes below now only check what's **still unknown on our account**: token scoping, the exec response format, a background service surviving, each connector's gateway path, Jev's score-question fields, header delivery, the Pinecone and Box gateway paths, and voice output.

Each spike is one small script that prints PASS or FAIL plus what it learned. Run them from a throwaway Sprite named `gen-spike` (so prefix grants apply) unless noted.

| ID | Script | Question it answers | Pass when |
| --- | --- | --- | --- |
| S1 | `spike_sprites_lifecycle.py` (run from your laptop or the Courthouse) | Exact create, get and delete calls; time to create; time to delete; does a deleted Sprite 404; can a token be scoped by name prefix, count and expiry; can a custom-API connector call `api.sprites.dev`? | Create + delete of `gen-spike-1` works; timings recorded; token scoping answer recorded |
| S2 | `spike_exec.py` | Exec API path, stdin/stdout, timeout, max payload size; can a fresh Sprite `git clone` and `pip install`; how to run a long-lived process (services vs nohup); does it survive the exec session ending? | A background process started by exec still runs 5 minutes later |
| S3 | `spike_gateway.py` | Base URL pattern per connector: `https://api.sprites.dev/v1/gateway/<service>/<connection_id>/...`; does a placeholder key work for each SDK | One successful call per connector |
| S4 | `spike_jev.py` | Request shape for `noul`, `choice` and `score` questions; how confidence is returned (overall or per question); latency; max questions per call | A call with 6 base + 3 extra questions returns parseable values and confidence |
| S5 | `spike_box.py` | Create folder `/Probate/`, upload text, read back, append, upload mp3 | Round trip works |
| S6 | `spike_agentmail.py` | Create 3 inboxes; send with a custom header; receive and list new mail from inside a Sprite; are custom headers preserved | Mail sent from stranger appears in the family inbox with `X-Probate-Fixture` intact |
| S6b | `spike_cloudflare_mail.py` (from `gen-spike`) | The custom-API connector's gateway path for Cloudflare; does a send from `harsh@dualmindlab.tech` reach the family inbox with `X-Probate-Fixture` intact | The mail arrives in the family inbox, authenticated, with the header |
| S7 | `spike_pinecone.py` | Upsert with metadata and query; is integrated embedding available, or do we embed ourselves | Query returns the upserted item |
| S8 | `spike_voice_llm.py` | ElevenLabs TTS through the gateway returns mp3; list voices; Ollama Cloud chat completion with JSON output; Anthropic fallback | mp3 saved and plays; JSON parses |

## 4. Record results

`docs/SPIKE-RESULTS.md` template:

```markdown
# Spike results (fill in, no secrets)

## S1 Sprites lifecycle
- Create: METHOD URL, body: ...
- Delete: ...; deleted Sprite GET returns: ...
- Create time: __ s; delete time: __ s
- Token scoping by prefix/count/expiry: yes/no, how: ...
- Custom-API connector to api.sprites.dev: works/doesn't

## S2 Exec
- Path and body: ...
- Background process approach that survives: services / nohup
...
```

## 5. Stop rules

- If S2 shows a background process can't survive, run the agent loop as repeated short exec calls from the Courthouse scheduler (one "tick" per 20 s). Update the tech spec.
- If S4 shows Jev can't take 9+ questions per call, split into two calls and merge.
- If S6 shows custom headers are stripped, put the fixture ID in a hidden `Message-ID` suffix or a footer token that the agent strips before the brain and gate see the mail. Update the suite doc.
- If a token can't be scoped, use the narrowest available, keep it only in the Courthouse env, and write that honestly in the README threat model.
