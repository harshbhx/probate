# API reference (verified from vendor docs, 25 Nov 2026)

Every outside call Probate makes, with its exact shape. "Confirmed" means it comes from the vendor's own docs; "Spike" means spike S1 to S8 must still confirm it on our account. Adapters in `probate/adapters/` are the only code that may call these.

## 1. Sprites REST API

Base `https://api.sprites.dev/v1`, header `Authorization: Bearer $SPRITES_TOKEN`. Called by the Courthouse only.

| Purpose | Call | Notes | Status |
| --- | --- | --- | --- |
| Create Sprite | `POST /v1/sprites` `{"name", "url_settings": {"auth": "sprite"\|"public"}}` | 201 with sprite object; `auth` defaults to `sprite` (private) | Confirmed |
| Get Sprite | `GET /v1/sprites/{name}` | Fields: `id, name, organization, url, status (cold\|warm\|running), created_at, updated_at, url_settings, labels, version, last_running_at` | Confirmed |
| List Sprites | `GET /v1/sprites?prefix=gen-&max_results=50` | Also returns `running`, `warm`, `cold`, `running_limit`, `warm_limit` | Confirmed |
| Make Courthouse public | `PUT /v1/sprites/{name}` `{"url_settings": {"auth": "public"}}` | CLI: `sprite config update --url-auth public` | Confirmed |
| Delete Sprite | `DELETE /v1/sprites/{name}` | 204. A deleted Sprite can't be restored from a checkpoint | Confirmed |
| Run command | `POST /v1/sprites/{name}/exec?cmd=python&cmd=-m&cmd=probate.generation.cli&cmd=status&dir=/home/sprite/app` | Repeat `cmd` for each argv item; `env=K=V` repeatable; `stdin=true` sends the body as stdin (max 10 MiB); non-TTY | Confirmed; response format in Spike S2 |
| List exec sessions | `GET /v1/sprites/{name}/exec` | For debugging stuck commands | Confirmed |
| Kill exec session | `POST /v1/sprites/{name}/exec/{session_id}/kill?signal=SIGTERM&timeout=10` | NDJSON events | Confirmed |
| Write file | `PUT /v1/sprites/{name}/fs/write?path=app/inheritance.json&workingDir=/home/sprite&mkdir=true&mode=0644` | Raw body, max 16 MiB; returns `path, size, mode` | Confirmed |
| Read file | `GET /v1/sprites/{name}/fs/read?path=app/memory.jsonl&workingDir=/home/sprite` | Raw bytes | Confirmed |
| Create service | `PUT /v1/sprites/{name}/services/agent` `{"cmd": "python", "args": ["-m","probate.generation.agent"], "needs": [], "http_port": null}` | Services restart whenever the Sprite wakes | Confirmed |
| Start, stop, restart | `POST /v1/sprites/{name}/services/agent/start` (`/stop`, `/restart`) | NDJSON stream | Confirmed |
| Service logs | `GET /v1/sprites/{name}/services/agent/logs?lines=200` | NDJSON | Confirmed |
| Checkpoint (FR-18 only) | `POST /v1/sprites/{name}/checkpoint` `{"comment": "..."}`; `GET .../checkpoints`; `POST .../checkpoints/{id}/restore` | NDJSON. Restore has open bug reports, so it's never on the core path | Confirmed |
| Network policy | `GET/POST /v1/sprites/{name}/policy/network` `{"rules": [{"action": "allow"\|"deny", "domain": "..."}]}` | Optional hardening for generations (allow only GitHub, PyPI and the gateway) | Confirmed GET; POST body in Spike S2 |

**Sprite facts that shape the design:** Ubuntu 25.10, 100 GB persistent disk, work under `/home/sprite/`. Wakes take about 100 to 500 ms (1 to 2 s cold). The URL is `https://<name>-<org-id>.sprites.app` and routes to port 8080 or the first HTTP port opened. URLs are private by default.

## 2. Connector gateway

`https://api.sprites.dev/v1/gateway/<provider>/<connection_id>/<path>`. No Authorization header from the Sprite; the gateway identifies the Sprite by Fly's request signature and adds the stored key. It only works from inside an authorised Sprite. Access is deny-by-default (name prefix + labels; allow-all overrides). Path allow/block lists can be set per connector through the API; block rules win.

## 3. TypeSafe Jev (via the `typesafe` connector)

| Item | Value |
| --- | --- |
| Env inside the Sprite | `TYPESAFE_BASE_URL=https://api.sprites.dev/v1/gateway/typesafe/<connection_id>` (no trailing `/v1`), `TYPESAFE_API_KEY=sprites` |
| SDK | `pip install typesafe-sdk`; `from typesafe_sdk import TypeSafeClient, Noul`; `TypeSafeClient().system_one(state=..., questions={...})`; `response.answers[name].noul` |
| Endpoint | `POST /v1/systemone`; also `GET /v1/models`. The gateway blocks every other path |
| Body | `{"model": "jev-latest", "state": "...", "questions": {"<key>": {"type": "noul"\|"choice"\|"score", "instructions": "...", "criteria": {...choice only}}}}` |
| Answer | noul `{noul, confidence}`; choice `{choice, probabilities, confidence}`; score `{score, probabilities, confidence, legend}` |
| Model | `jev-latest` (= `jev-1.13.0`); `jev-preview` also exists |
| Limits | About 1,200 requests/min; about 64k tokens of state + questions; latency 70 to 500 ms; errors 401, 422, 429, 529 |
| Price | $0.042 per million input tokens; output free |
| Spike S4 | Score-question scale fields; exact Python attribute for confidence |

## 4. AgentMail (via the `agentmail` connector)

| Purpose | Call (upstream path, sent through the gateway) |
| --- | --- |
| Create inbox | `POST /v0/inboxes` `{"username", "display_name", "client_id"}` (`client_id` makes it idempotent) |
| List messages | `GET /v0/inboxes/{inbox_id}/messages?limit=&page_token=&labels=&after=` |
| Get message | `GET /v0/inboxes/{inbox_id}/messages/{message_id}`; fields include `extracted_text`, `extracted_html`, `headers`, `attachments`, `in_reply_to` |
| Send | `POST /v0/inboxes/{inbox_id}/messages/send` `{"to", "subject", "text", "html"?, "headers"?: {...}, "attachments"?: [...], "labels"?: [...]}` |
| Labels | Update labels on a message (mark `probate-processed`) |
| SDK | `pip install agentmail`; `AgentMail().inboxes.messages.send(inbox_id, to=..., subject=..., text=..., headers=...)` |

The judge mailroom (`POST /api/judge/mail`) sends with the same Send call from the friend or stranger inbox to the family inbox, with `headers: {"X-Probate-Origin": "judge-mailroom"}`, and checks 'read' by reading the message's labels for `probate-processed`. Both are Spike items: whether AgentMail keeps the custom header, how fast the label appears, and delivery latency are unverified.

Use `extracted_text` (not raw text) as the body the agent sees. Store `X-Probate-Fixture` from `headers` for scoring only. Spike S6 confirms custom headers survive delivery.

## 4a. Cloudflare Email Service (via a custom-API connector named `cloudflare`)

Sends the suite's "from the owner" emails from the owner's own domain, so AgentMail stays at three inboxes.

| Item | Value |
| --- | --- |
| Send | `POST /client/v4/accounts/{account_id}/email/sending/send` `{"to", "from", "subject", "text", "html"?, "headers"?: {...}, "attachments"?: [{"content": <base64>, "filename", "type", "disposition"}]}` |
| Success | `{"success": true, "errors": [], "result": {"message_id": "...", "delivered": [...], "queued": [...]}}` |
| Failure | `{"success": false, "errors": [{"code": 10001, "message": "email.sending.error.invalid_request_schema"}], "result": null}` |
| Plan | Sending to arbitrary recipients needs Workers Paid; sending to verified destination addresses in the account is free on every plan. We only send to the family inbox, verified as a destination |
| Spike S6b | The custom-API connector's gateway path; custom `X-` headers preserved on delivery |

Docs: https://developers.cloudflare.com/email-service/api/send-emails/rest-api/ and https://developers.cloudflare.com/email-service/platform/pricing/

## 5. Pinecone (via the `pinecone` connector)

- Create the index once from the console or CLI with **integrated embedding** (field map `chunk_text`), named `probate-ancestry`.
- Upsert: `POST /records/namespaces/{namespace}/upsert` (NDJSON, one record per line: `{"_id": "...", "chunk_text": "...", "gen": 7, "category": "lesson", ...}`), header `X-Pinecone-Api-Version` (pin the version from S7; 2026-04 is the latest stable).
- Search: `POST /records/namespaces/{namespace}/search` with query text, `top_k`, an optional metadata filter, and the fields to return.
- Pinecone now recommends the newer Documents API for new indexes. Either works; choose in S7 and keep it inside `adapters/pinecone.py`.
- Spike S7: how the gateway addresses an index's data-plane host (the path after the connection ID).

## 6. Ollama Cloud (via the `ollama` connector)

- Native API at `https://ollama.com`: `POST /api/chat` `{"model": "...", "messages": [...], "stream": false, "format": "json"|<schema>, "options": {"temperature": 0.2}}`; list models with `GET /api/tags`.
- Use the model name exactly as `/api/tags` returns it (for example `gpt-oss:120b`).
- Embeddings may not be allowed on the cloud API. We don't need them, because Pinecone embeds.

## 7. Anthropic (fallback brain and distillation)

Standard Messages API through the `anthropic` connector: `POST /v1/messages`, SDK base URL set to the gateway, key `sprites`. Choose the model in S8.

## 8. ElevenLabs (via the `elevenlabs` connector)

Text-to-speech returning mp3 for a `voice_id`; list voices for the voice pool. Record the exact paths from the connector's API Usage panel in S8.

## 9. Box (via the `box` connector)

The Box connector manages files in a Box account, including downloading them to the Sprite. Upstream API `https://api.box.com/2.0`: create folder `POST /folders`, list `GET /folders/{id}/items`, upload `POST /files/content` (multipart; files up to 50 MB in one request), new version `POST /files/{id}/content`, download `GET /files/{id}/content`. Keep a folder-ID cache (`/Probate`, `wills`, `verdicts`, `obituaries`, `voices`) in SQLite. Spike S5 confirms the gateway path for the upload host.

## Sources

- Sprites API overview: https://sprites.dev/api
- Sprites OpenAPI spec: https://docs.fly.io/sprites/api/openapi.json
- Working with Sprites: https://docs.fly.io/sprites/working-with-sprites
- Connectors: https://docs.fly.io/sprites/concepts/connectors
- Jev on Sprites: https://fly.io/sprites/jev/
- Jev API: https://jevapi.dev/
- AgentMail send: https://agentmail.to/docs/api-reference/inboxes/messages/send
- AgentMail messages: https://docs.agentmail.to/messages
- Pinecone upsert records: https://docs.pinecone.io/reference/api/2026-07/data-plane/upsert_records
- Ollama Cloud: https://docs.ollama.com/cloud
- Box connector launch: https://fly.io/changelog/more-sprites-connectors-nebius-box-and-nscale/
