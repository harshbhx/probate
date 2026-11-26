# probate-mcp

A small, read-only [Model Context Protocol](https://modelcontextprotocol.io) server for Probate. It lets any MCP client look at the family: who is alive, how each generation's trial went, what the instincts are, and what the evidence says.

[![npm](https://img.shields.io/npm/v/probate-mcp)](https://www.npmjs.com/package/probate-mcp) [![license: MIT](https://img.shields.io/npm/l/probate-mcp)](https://github.com/harshbhx/probate/blob/main/LICENSE) [![repo](https://img.shields.io/badge/repo-harshbhx%2Fprobate-blue?logo=github)](https://github.com/harshbhx/probate)

It talks to the Courthouse's public API over HTTP `GET` and nothing else. There are no write or admin tools, and the admin token is never read or sent. Also mirrored on GitHub Packages as `@harshbhx/probate-mcp`.

## Install

Nothing to install if your client runs it with `npx` (Node 20+):

```sh
npx -y probate-mcp
```

Or add it globally with `npm install -g probate-mcp`.

## Usage

The server needs a running Courthouse. `PROBATE_API_URL` is its address and defaults to `http://localhost:8080`. For a local family, run `make sim` then `make api` in the [repo](https://github.com/harshbhx/probate) first. Simulated data is labelled as such in the summary's `mode` field.

Claude Code:

```sh
claude mcp add probate --env PROBATE_API_URL=http://localhost:8080 -- npx -y probate-mcp
```

Claude Desktop, Cursor and other clients (the file is usually JSON with an `mcpServers` key):

```json
{
  "mcpServers": {
    "probate": {
      "command": "npx",
      "args": ["-y", "probate-mcp"],
      "env": { "PROBATE_API_URL": "http://localhost:8080" }
    }
  }
}
```

If the Courthouse cannot be reached, a tool answers with an error that names the address it tried and how to fix it.

## Tools

| Tool | Courthouse route | Returns |
| --- | --- | --- |
| `get_summary` | `/api/summary` | The family at a glance: who is alive, counts, curve, latest trial, run mode |
| `list_generations` | `/api/summary` | Every generation with status and headline numbers |
| `get_generation` (`n`) | `/api/generations/{n}` | One generation: eulogy, numbers, the timeline of its day |
| `get_trial` (`n`) | `/api/trials/{n}` | Every line of its will with the verdict, and what passed down |
| `get_latest_trial` | `/api/trials/latest` | The most recent trial |
| `get_instincts` | `/api/genome` | Every instinct learned so far |
| `get_evidence` | `/api/evidence` | Tricks resisted per generation, and the test-by-generation grid |

All seven tools are marked read-only.

## Part of Probate

This is one piece of [Probate](https://github.com/harshbhx/probate), an email agent that lives one generation at a time and passes down only what a court approves. Built for Fly.io Hacksgiving 2026.

- Repository: [github.com/harshbhx/probate](https://github.com/harshbhx/probate)
- Live site: [probate.dualmindlab.tech](https://probate.dualmindlab.tech)
- Docs for this package: [For AI agents](https://probate.dualmindlab.tech/docs/reference/agents) and [Everything we built](https://probate.dualmindlab.tech/docs/products)
- The story: [the Probate write-up](https://probate.dualmindlab.tech/article)
- Related: [probate-client](https://www.npmjs.com/package/probate-client) (npm), [probate-client](https://pypi.org/project/probate-client/) (PyPI), [probate-memory-court](https://pypi.org/project/probate-memory-court/) (PyPI)
- Releases: [v0.1.0](https://github.com/harshbhx/probate/releases/tag/v0.1.0), [v0.2.0](https://github.com/harshbhx/probate/releases/tag/v0.2.0)

## Development

```sh
npm install                       # in the monorepo root
npm run build -w probate-mcp
npm run lint -w probate-mcp
PROBATE_API_URL=http://localhost:8080 node packages/mcp/dist/server.js
PROBATE_API_URL=http://localhost:8080 npm run smoke -w probate-mcp   # starts the server, lists the tools, calls each one
```

## License

MIT. Copyright (c) 2026 Harsh Bhanushali.
