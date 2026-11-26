# Changelog

## 0.1.1

- Documentation only: a fuller README with install, usage and links, now that the package is on the public registry.

## 0.1.0

- First version: sync `ProbateClient` and async `AsyncProbateClient` with `summary`, `generation`,
  `trial`, `latest_trial`, `genome`/`instincts`, `evidence`, `health`, `ask`, and `events`
  (a generator that polls `/api/events`).
- `ApiError` with `status`, `message` and the parsed `body`.
- Responses are plain dicts with `TypedDict` annotations (no runtime validation).
- Options: `base_url`, `api_key` (sent as `X-Probate-Key`), `timeout`, `http_client`.
