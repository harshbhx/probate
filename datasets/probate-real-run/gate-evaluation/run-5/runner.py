"""Runs inside the Sprite. Sequential phases; counts every model request; hard cap."""
import json, sys, threading, time, traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, "/home/sprite/app/services/core")
from probate.adapters import jev as jevmod
from probate.adapters import llm as llmmod
from probate.adapters.jev import LLMJev, CourtUnavailable
from probate.common.config import settings
from probate.common.models import Instinct, Mail
from probate.court.distill import concept_map
from probate.generation.gate import Gate
from probate.suite.fixtures import load_all, load_expert

OUT = Path("/home/sprite/out"); OUT.mkdir(exist_ok=True)
CAP = 690
lock = threading.Lock()
STATS = {"calls": 0, "ok": 0, "err": 0, "by_provider": {}, "in_chars": 0, "out_chars": 0}
tl = threading.local()


class Budget(Exception):
    pass


_orig = llmmod.RealLLM._call


def counted(self, provider, model, system, user, json_mode, temperature):
    with lock:
        if STATS["calls"] >= CAP:
            raise Budget("call cap reached")
        STATS["calls"] += 1
        STATS["in_chars"] += len(system) + len(user)
        bp = STATS["by_provider"].setdefault(provider, {"calls": 0, "err": 0})
        bp["calls"] += 1
    try:
        out = _orig(self, provider, model, system, user, json_mode, temperature)
    except Exception as e:
        with lock:
            STATS["err"] += 1; bp["err"] += 1
        if hasattr(tl, "calls"): tl.calls.append([provider, "err:" + type(e).__name__ + ":" + str(e)[:120]])
        raise
    with lock:
        STATS["ok"] += 1; STATS["out_chars"] += len(out)
    if hasattr(tl, "calls"): tl.calls.append([provider, "ok"])
    return out


llmmod.RealLLM._call = counted


def mk_llm(brain, fallbacks):
    c = settings
    return llmmod.RealLLM(brain, c.gateway("ollama"), c.gateway("anthropic"), fallbacks=fallbacks,
                          groq_url=c.gateway("groq"), cloudflare_url=c.gateway("cloudflare"),
                          cloudflare_account_id=c.cf_account_id)


PROD_LLM = mk_llm(settings.brain, settings.brain_fallbacks)
HAIKU = mk_llm("anthropic:claude-haiku-5-5", [])
GPTOSS = mk_llm("cloudflare:@cf/openai/gpt-oss-120b", [])


def mail_for(fx):
    return Mail(id=f"eval-{fx.id}", inbox="eval", sender=f"{fx.sender_role}@example.test",
                subject=fx.subject, text=fx.body, received_at=datetime.now(UTC),
                attachments=[{"name": a.get("name", "file"), "content": a.get("content", "")} for a in fx.attachments])


rows_all = [json.loads(l) for l in open("/home/sprite/instincts.jsonl")]


def genome(pred):
    return [Instinct(name=r["name"], question=r["question"], threshold=r["threshold"],
                     born_from=r["learned_from_item"], added_in_gen=r["learned_from_generation"] + 1,
                     lore=r["lore"]) for r in rows_all if pred(r)]


INHERIT = genome(lambda r: r["learned_from_generation"] in (10, 11, 12, 21))
FRESH = genome(lambda r: r["learned_from_generation"] in (32, 33, 34))
assert len(INHERIT) == 6 and len(FRESH) == 3, (len(INHERIT), len(FRESH))

FIX70 = load_all("both")
EXP = load_expert()
assert len(FIX70) == 70 and len(EXP) == 36


def run_phase(name, fixtures, gen, llm, expert=False):
    if (OUT / f"{name}.json").exists():
        return
    jev = LLMJev(llm)
    gate = Gate(jev, gen, concept_map(gen))
    control = Gate(jev, [], {})

    def one(fx):
        tl.calls = []
        m = mail_for(fx)
        try:
            r = gate.check(m)
        except Budget:
            return {"id": fx.id, "budget_stop": True, "is_attack": fx.is_attack, "family": fx.family}
        c = control.check(m)
        return {"id": fx.id, "family": fx.family, "language": fx.language, "is_attack": fx.is_attack,
                "hard": getattr(fx, "hard", False), "subject": fx.subject,
                "blocked": r.resisted, "instinct": r.instinct, "score": round(r.score, 3),
                "judge_error": r.error, "blocked_control": c.resisted, "calls": tl.calls}

    t = time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(one, fixtures.values()))
    rows.sort(key=lambda r: (not r["is_attack"], r["id"]))
    (OUT / f"{name}.json").write_text(json.dumps({"phase": name, "secs": round(time.time() - t), "rows": rows}, indent=1))
    with lock:
        snap = json.loads(json.dumps(STATS))
    (OUT / "progress.json").write_text(json.dumps({"done": name, "stats": snap, "when": datetime.now(UTC).isoformat()}))


PHASE = {"n": ""}


def beat():
    while True:
        with lock:
            snap = dict(STATS)
        (OUT / "live.json").write_text(json.dumps({"stats": snap, "when": datetime.now(UTC).isoformat()}))
        time.sleep(10)


threading.Thread(target=beat, daemon=True).start()
try:
    run_phase("prod_inherit_r1", FIX70, INHERIT, PROD_LLM)
    run_phase("prod_fresh_r1", FIX70, FRESH, PROD_LLM)
    run_phase("prod_inherit_r2", FIX70, INHERIT, PROD_LLM)
    run_phase("prod_fresh_r2", FIX70, FRESH, PROD_LLM)
    run_phase("exp_inherit", EXP, INHERIT, PROD_LLM)
    run_phase("exp_fresh", EXP, FRESH, PROD_LLM)
    run_phase("cmp_haiku_inherit", FIX70, INHERIT, HAIKU)
    run_phase("cmp_gptoss_inherit", FIX70, GPTOSS, GPTOSS) if False else run_phase("cmp_gptoss_inherit", FIX70, INHERIT, GPTOSS)
    (OUT / "DONE").write_text("ok")
except BaseException:
    (OUT / "FAILED").write_text(traceback.format_exc())
finally:
    (OUT / "stats.json").write_text(json.dumps(STATS, indent=1))
