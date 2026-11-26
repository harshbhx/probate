# Sprites connectors from Probate

Connector manifests we wrote for [Fly.io Sprites](https://sprites.dev), to contribute to Fly's community catalog at [superfly/sprites-connectors](https://github.com/superfly/sprites-connectors). Once merged, any Sprite can use them, not just Probate.

| Connector | What a Sprite can do with it | Status |
| --- | --- | --- |
| [`apify`](apify/connector.json) | Run any [Apify](https://apify.com) Actor or saved task, poll and abort its runs, read the datasets and records it produces, and search Apify Store. Probate's generations use it to read the pages emails link to (card P1) | Manifest valid against `v1/schema.json`; icons and a live probe still to do |

Probate itself used Apify through a Custom API connector while this one waited for review. The two are interchangeable: set `PROBATE_CONNECTIONS` to `"apify": "<connection id>"` for this connector, or `"apify": "custom_api/<id>"` for a Custom API one (see `docs/06-SETUP-AND-SPIKES.md`).

## What's in the manifest

- **Auth:** the Apify token as a bearer token. The Sprite never holds it.
- **Probe:** `GET /v2/users/me`, which costs nothing, and must answer with `data.id` and `data.username`.
- **Routes:** running Actors and tasks (`/runs`, `/run-sync`, `/run-sync-get-dataset-items`), reading and aborting runs and their logs, reading datasets and key-value records, reading an Actor, and searching Apify Store. Nothing that manages tokens, the account, billing, webhooks, schedules, Actors or tasks, and no direct writes to storages.
- **Actor ids** contain `~` (`apify~rag-web-browser`), so `path_param` allows letters, digits, `.`, `_`, `~` and `-`.
- **Timeouts:** the gateway waits 120 seconds; the usage notes tell Sprites to pass `?timeout=100` on `run-sync` routes or to start a run and poll it.

## To submit it (the owner)

In a fork of `superfly/sprites-connectors`:

```sh
node scripts/new.mjs apify                       # creates connectors/apify/ from the template
cp <probate>/integrations/sprites-connectors/apify/connector.json connectors/apify/
# icon.svg: Apify's logo from https://apify.com/press-kit (note its licence in the PR)
# mark.svg: the same logo in one colour, every fill currentColor, ids prefixed apify-
node scripts/check-connectors.mjs apify
npx --yes ajv-cli@5 validate --spec=draft2020 --strict=false -s v1/schema.json -d connectors/apify/connector.json
APIFY_TOKEN=... node scripts/probe.mjs apify --key-env APIFY_TOKEN --write-fixture
APIFY_TOKEN=wrong node scripts/probe.mjs apify --key-env APIFY_TOKEN   # must fail
```

Then open the pull request with the icon's source and licence, the vendor docs for each route (below), and the probe recording under `fixtures/apify/`.

## Vendor docs

Every route is in Apify's API reference, https://docs.apify.com/api/v2, under Users, Store, Actors, Actor tasks, Actor runs, Datasets and Key-value stores. The one Probate depends on is https://docs.apify.com/api/v2/act-run-sync-get-dataset-items-post. Link each route's page in the pull request.
