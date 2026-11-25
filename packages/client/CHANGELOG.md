# Changelog

## 0.1.0 (unreleased)

- First version: `summary`, `generation`, `trial`, `latestTrial`, `genome`/`instincts`,
  `evidence`, `health`, `ask`, and `events` (an async iterator that polls `/api/events`).
- `ApiError` with `status`, `message` and the parsed `body`.
- Options: `baseUrl`, `apiKey` (sent as `X-Probate-Key`), `timeout`, `signal`, `fetch`.
