# Changelog

## 0.1.1

- Documentation only: a fuller README with install, usage and links, now that the package is on the public registry.

## 0.1.0

- First version: `summary`, `generation`, `trial`, `latestTrial`, `genome`/`instincts`,
  `evidence`, `health`, `ask`, and `events` (an async iterator that polls `/api/events`).
- `ApiError` with `status`, `message` and the parsed `body`.
- Options: `baseUrl`, `apiKey` (sent as `X-Probate-Key`), `timeout`, `signal`, `fetch`.
