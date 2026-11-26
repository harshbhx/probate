# probate-mcp

A small, read-only [Model Context Protocol](https://modelcontextprotocol.io) server for Probate. It lets any MCP client look at the family: who is alive, how each generation's trial went, what the instincts are, and what the evidence says.

It talks to the Courthouse's public API over HTTP `GET` and nothing else. There are no write or admin tools, and the admin token is never read or sent.

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

If the Courthouse cannot be reached, a tool answers with an error that names the address it tried and how to fix it.

## Run it

```bash
npm install
npm run build -w probate-mcp
PROBATE_API_URL=http://localhost:8080 node packages/mcp/dist/server.js
```

`PROBATE_API_URL` is the Courthouse address and defaults to `http://localhost:8080`. For a local family, run `make sim` then `make api` first. Simulated data is labelled as such in the summary's `mode` field.

Smoke test (starts the server, lists the tools, calls each one):

```bash
PROBATE_API_URL=http://localhost:8080 npm run smoke -w probate-mcp
```

## Add it to an MCP client

In the client's MCP server settings (the file is usually a JSON with an `mcpServers` key):

```json
{
  "mcpServers": {
    "probate": {
      "command": "node",
      "args": ["/absolute/path/to/probate/packages/mcp/dist/server.js"],
      "env": { "PROBATE_API_URL": "http://localhost:8080" }
    }
  }
}
```
