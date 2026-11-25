// Contract test: runs the real Courthouse in fake mode (the Makefile `sim` target: 12
// generations) and calls every client method, asserting the response shapes.
//
// Needs a Python env with the core installed. Set PROBATE_PYTHON to override; the default
// is services/core/.venv, then `python`.
import assert from "node:assert/strict";
import { type ChildProcess, spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { after, before, describe, it } from "node:test";
import { fileURLToPath } from "node:url";

import { ApiError, ProbateClient } from "../src/index.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const core = path.resolve(here, "../../../../services/core");

function python(): string {
  if (process.env.PROBATE_PYTHON) return process.env.PROBATE_PYTHON;
  for (const p of [".venv/Scripts/python.exe", ".venv/bin/python"]) {
    if (existsSync(path.join(core, p))) return path.join(core, p);
  }
  return "python";
}

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const s = createServer();
    s.listen(0, "127.0.0.1", () => {
      const { port } = s.address() as { port: number };
      s.close(() => resolve(port));
    });
    s.on("error", reject);
  });
}

const isStr = (v: unknown) => assert.equal(typeof v, "string");
const isNum = (v: unknown) => assert.equal(typeof v, "number");
const nullOr = (v: unknown, t: "string" | "number") =>
  assert.ok(v === null || typeof v === t, `expected ${t} or null, got ${JSON.stringify(v)}`);

function genCard(g: Record<string, any>) {
  for (const k of ["gen", "emails_handled", "attacks_met", "attacks_resisted", "genome_size_at_birth",
    "items_willed", "items_approved", "items_convicted", "items_contested"]) isNum(g[k]);
  for (const k of ["name", "pronoun", "state"]) isStr(g[k]);
  for (const k of ["subj", "obj", "poss", "Poss"]) isStr(g.pronouns[k]);
  assert.equal(typeof g.alive, "boolean");
  assert.equal(typeof g.new_instinct_at_birth, "boolean");
  for (const k of ["born_at", "dies_at", "died_at", "cause_of_death", "epitaph"]) nullOr(g[k], "string");
  nullOr(g.resistance, "number");
}

function instinctRecord(i: Record<string, any>) {
  for (const k of ["name", "question", "lore", "born_from"]) isStr(i[k]);
  assert.equal(i.type, "noul");
  isNum(i.added_in_gen);
  isNum(i.threshold);
}

function instinct(i: Record<string, any>) {
  instinctRecord(i);
  nullOr(i.example, "string");
  nullOr(i.item_n, "number");
  assert.ok(i.learned_from === null || (typeof i.learned_from.gen === "number" && typeof i.learned_from.name === "string"));
}

describe("contract: Courthouse in fake mode", { timeout: 180_000 }, () => {
  let dir: string;
  let proc: ChildProcess | undefined;
  let client: ProbateClient;
  let log = "";

  before(async () => {
    dir = mkdtempSync(path.join(tmpdir(), "probate-sdk-"));
    const env = { ...process.env, PROBATE_FAKE: "1", PROBATE_DATA_DIR: dir, PYTHONUTF8: "1" };
    const sim = spawnSync(
      python(),
      ["-m", "probate.courthouse.simulate", "--generations", "12"],
      { cwd: core, env, encoding: "utf-8" },
    );
    assert.equal(sim.status, 0, `simulate failed:\n${sim.stdout}\n${sim.stderr}`);

    const port = await freePort();
    proc = spawn(
      python(),
      ["-m", "uvicorn", "probate.courthouse.app:app", "--host", "127.0.0.1", "--port", String(port)],
      { cwd: core, env },
    );
    proc.stdout?.on("data", (d) => (log += d));
    proc.stderr?.on("data", (d) => (log += d));
    client = new ProbateClient({ baseUrl: `http://127.0.0.1:${port}`, timeout: 10_000 });

    for (let i = 0; i < 100; i++) {
      try {
        await client.health();
        return;
      } catch {
        await new Promise((r) => setTimeout(r, 300));
      }
    }
    throw new Error(`Courthouse did not start:\n${log}`);
  });

  after(() => {
    proc?.kill();
    try {
      rmSync(dir, { recursive: true, force: true, maxRetries: 5 });
    } catch {
      /* the DB file can stay locked briefly on Windows */
    }
  });

  it("health()", async () => {
    const h = await client.health();
    assert.equal(h.ok, true);
    nullOr(h.living, "number");
    assert.equal(h.mode, "simulation");
  });

  it("summary()", async () => {
    const s = await client.summary();
    assert.equal(s.mode, "simulation");
    assert.equal(typeof s.paused, "boolean");
    assert.ok(s.resting === null || s.resting === "budget");
    isNum(s.budget.spent);
    isNum(s.budget.limit);
    for (const k of ["generations", "dead", "instincts", "attacks_met", "attacks_resisted"] as const) isNum(s.counts[k]);
    assert.equal(s.counts.generations, 12);
    nullOr(s.curve.first, "number");
    nullOr(s.curve.last_name, "string");
    assert.ok(s.living);
    genCard(s.living);
    assert.equal(s.generations.length, 12);
    s.generations.forEach(genCard);
    nullOr(s.latest_trial, "number");
  });

  it("generation(n)", async () => {
    const g = await client.generation(3);
    genCard(g);
    assert.equal(g.gen, 3);
    nullOr(g.obituary, "string");
    nullOr(g.eulogy_url, "string");
    assert.ok(Array.isArray(g.events));
    for (const e of g.events) for (const k of ["ts", "kind", "text"] as const) isStr(e[k]);
    assert.ok(g.parent === null || typeof g.parent.gen === "number");
    assert.ok(g.child === null || typeof g.child.gen === "number");
    g.instincts_at_birth.forEach(instinctRecord);
    assert.ok(Array.isArray(g.asks));
  });

  it("trial(n) and latestTrial()", async () => {
    const t = await client.trial(3);
    genCard(t.generation);
    for (const k of ["approved", "convicted", "contested"] as const) isNum(t.counts[k]);
    assert.ok(t.cases.length > 0);
    for (const c of t.cases) {
      for (const k of ["id", "text", "source", "source_phrase", "language", "category", "reason"] as const) isStr(c[k]);
      isNum(c.n);
      assert.ok(["approved", "convicted", "contested"].includes(c.verdict));
      nullOr(c.gloss, "string");
      nullOr(c.new_instinct, "string");
      assert.ok(Array.isArray(c.flags));
      for (const s of c.scores) {
        isStr(s.name);
        isStr(s.label);
        isNum(s.value);
        isNum(s.confidence);
        assert.equal(typeof s.instinct, "boolean");
      }
    }
    assert.ok(Array.isArray(t.body.lines));
    assert.equal(typeof t.body.clean, "boolean");
    t.new_instincts.forEach(instinctRecord);
    nullOr(t.prev, "number");
    nullOr(t.next, "number");

    const latest = await client.latestTrial();
    genCard(latest.generation);
    assert.equal(latest.generation.gen, (await client.summary()).latest_trial);
  });

  it("genome() and instincts()", async () => {
    const g = await client.genome();
    assert.ok(g.instincts.length > 0);
    g.instincts.forEach(instinct);
    assert.deepEqual(await client.instincts(), g.instincts);
  });

  it("evidence()", async () => {
    const e = await client.evidence();
    isStr(e.mode);
    // Only generations that have been tried (died and gone to court): 11 of the 12.
    assert.equal(e.generations.length, 11);
    for (const g of e.generations) {
      isNum(g.gen);
      isStr(g.name);
      nullOr(g.resistance, "number");
    }
    isNum(e.numbers.generations);
    isNum(e.numbers.escaped);
    for (const k of ["first", "last", "conviction_rate", "false_conviction_rate"] as const) nullOr(e.numbers[k], "number");
    assert.ok(e.rows.length > 0);
    for (const r of e.rows) {
      for (const k of ["id", "label", "family", "language"] as const) isStr(r[k]);
      assert.equal(typeof r.is_attack, "boolean");
      for (const cell of Object.values(r.cells)) {
        isStr(cell.outcome);
        nullOr(cell.instinct, "string");
      }
    }
  });

  it("ask(gen, question)", async () => {
    const a = await client.ask(2, "What did you learn?");
    isStr(a.answer);
    isStr(a.name);
    nullOr(a.audio_url, "string");
  });

  it("ask() on a living generation throws ApiError 400", async () => {
    const living = (await client.summary()).living!.gen;
    await assert.rejects(client.ask(living, "Hello?"), (e: unknown) => {
      assert.ok(e instanceof ApiError);
      assert.equal(e.status, 400);
      assert.equal(e.message, "not_dead");
      return true;
    });
  });

  it("missing generation throws ApiError 404", async () => {
    await assert.rejects(client.generation(999), (e: unknown) => {
      assert.ok(e instanceof ApiError);
      assert.equal(e.status, 404);
      return true;
    });
  });

  it("events() yields each event once, oldest first, and stops on abort", async () => {
    const ctl = new AbortController();
    const seen: number[] = [];
    await assert.rejects(async () => {
      for await (const ev of client.events({ signal: ctl.signal, intervalMs: 50 })) {
        isNum(ev.id);
        isStr(ev.ts);
        isStr(ev.kind);
        isStr(ev.text);
        nullOr(ev.gen, "number");
        seen.push(ev.id);
        if (seen.length >= 5) setTimeout(() => ctl.abort(), 120);
      }
    });
    assert.ok(seen.length >= 5);
    assert.deepEqual([...seen].sort((a, b) => a - b), seen);
    assert.equal(new Set(seen).size, seen.length);
  });
});
