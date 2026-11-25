# probate-client (Python)

A small typed client for the [Probate](https://github.com/harshbhx/probate) Courthouse public API,
with sync and async versions. It depends only on `httpx`. Python 3.11+.

Not yet published to PyPI. Until then: `pip install ./packages/client-py` from a checkout.

```sh
pip install probate-client
```

## Use

```python
from probate_client import ApiError, ProbateClient

with ProbateClient("https://your-courthouse.example") as probate:
    summary = probate.summary()
    print(summary["living"], summary["counts"]["instincts"])

    for case in probate.latest_trial()["cases"]:
        print(case["n"], case["verdict"], case["text"])

    try:
        print(probate.ask(3, "What would you warn the next one about?")["answer"])
    except ApiError as e:
        print(e.status, e.message)  # 400 "not_dead", 429 "rate_limited", ...

    for event in probate.events(interval=5):  # polls; break to stop
        print(event["ts"], event["kind"], event["text"])
```

Async:

```python
import asyncio
from probate_client import AsyncProbateClient

async def main():
    async with AsyncProbateClient("http://localhost:8080") as probate:
        print(await probate.health())
        async for event in probate.events():
            print(event["text"])

asyncio.run(main())
```

## API

| Method | Route |
| --- | --- |
| `summary()` | `GET /api/summary` |
| `generation(n)` | `GET /api/generations/{n}` |
| `trial(n)` | `GET /api/trials/{n}` |
| `latest_trial()` | `GET /api/trials/latest` |
| `genome()` / `instincts()` | `GET /api/genome` (`instincts()` returns just the list) |
| `evidence()` | `GET /api/evidence` |
| `health()` | `GET /healthz` |
| `ask(gen, question)` | `POST /api/generations/{n}/ask` |
| `events(since=0, interval=5.0)` | `GET /api/events?since=` (iterator) |

`ProbateClient(base_url="http://localhost:8080", *, api_key=None, timeout=30.0, http_client=None)`, and the
same for `AsyncProbateClient` (use `await client.aclose()` or `async with`). Errors from the server raise
`ApiError` with `status`, `message` and `body`. Network errors and timeouts raise the `httpx` exceptions
unchanged. Nothing is retried.

Responses are plain dicts. `probate_client.types` has `TypedDict` definitions for them, so editors and mypy
know the keys.

## Honest limits

- **`events()` polls.** The Courthouse serves `/api/events` as a JSON list (newest 50 rows, `?since=<id>`),
  not as server-sent events. If more than 50 events arrive between polls, the older ones are missed.
- **`api_key` does nothing yet.** It is sent as `X-Probate-Key`, reserved for a future judge key; the
  Courthouse does not read it today.
- **No runtime validation.** The `TypedDict`s are hand-written from `services/core/probate/courthouse/views.py`
  and checked in the tests against a fake-mode Courthouse (12 simulated generations, missing and extra
  keys both fail). A server change that the tests do not cover can still drift.
- **`ask` only works on dead generations** and is limited to 10 questions a minute per IP.
- No retries, no pagination helpers, no caching.

## Develop

```sh
pip install -e services/core            # the Courthouse the tests run against
pip install -e 'packages/client-py[dev]'
ruff check packages/client-py
pytest packages/client-py
```

MIT licensed.
