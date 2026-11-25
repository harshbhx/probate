"""Write the Courthouse's OpenAPI schema for the docs site's API reference.

    make api-spec        (or: services/core/.venv/bin/python scripts/export_openapi.py)

FastAPI gives the routes, parameters and descriptions. The response examples and schemas come
from a real simulated family: the script runs `make sim` into a temporary folder, calls every
read route, and records what came back. Nothing in the examples is written by hand.

Set PROBATE_PUBLIC_URL to the live Courthouse so the docs playground can call it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "services" / "core"
OUT = ROOT / "apps" / "site" / "openapi.json"
LIST_SAMPLE = 2  # list items kept in each example, so the schema file stays readable

# Short operation IDs: they name the docs pages (/docs/reference/api/<tag>/<id>).
OPERATION_IDS = {
    ("get", "/healthz"): "health",
    ("get", "/api/summary"): "summary",
    ("get", "/api/generations/{gen}"): "generation",
    ("get", "/api/trials/latest"): "latest-trial",
    ("get", "/api/trials/{gen}"): "trial",
    ("get", "/api/genome"): "genome",
    ("get", "/api/evidence"): "evidence",
    ("get", "/api/events"): "events",
    ("post", "/api/generations/{gen}/ask"): "ask",
    ("get", "/audio/{name}"): "audio",
    ("post", "/admin/pause"): "pause",
    ("post", "/admin/resume"): "resume",
    ("post", "/admin/force-death"): "force-death",
    ("post", "/admin/contested/{item_id}"): "decide",
    ("post", "/admin/tick"): "tick",
}

READS = {
    "/healthz": "/healthz",
    "/api/summary": "/api/summary",
    "/api/generations/{gen}": "/api/generations/2",
    "/api/trials/latest": "/api/trials/latest",
    "/api/trials/{gen}": "/api/trials/3",
    "/api/genome": "/api/genome",
    "/api/evidence": "/api/evidence",
    "/api/events": "/api/events?since=0",
}


def infer(samples: list) -> dict:
    """A JSON schema that every sample fits."""
    kinds: dict[str, list] = {}
    for v in samples:
        kind = (
            "null"
            if v is None
            else "boolean"
            if isinstance(v, bool)
            else "integer"
            if isinstance(v, int)
            else "number"
            if isinstance(v, float)
            else "string"
            if isinstance(v, str)
            else "array"
            if isinstance(v, list)
            else "object"
        )
        kinds.setdefault(kind, []).append(v)
    if "integer" in kinds and "number" in kinds:
        kinds["number"] += kinds.pop("integer")
    schemas = []
    for kind, vals in kinds.items():
        if kind == "object":
            keys: dict[str, list] = {}
            for obj in vals:
                for k, val in obj.items():
                    keys.setdefault(k, []).append(val)
            always = [k for k in keys if all(k in obj for obj in vals)]
            schema = {"type": "object", "properties": {k: infer(v) for k, v in keys.items()}}
            if always:
                schema["required"] = always
            schemas.append(schema)
        elif kind == "array":
            items = [x for arr in vals for x in arr]
            schemas.append({"type": "array", "items": infer(items) if items else {}})
        else:
            schemas.append({"type": kind})
    if len(schemas) == 1:
        return schemas[0]
    if all(set(s) == {"type"} for s in schemas):
        return {"type": [s["type"] for s in schemas]}
    return {"anyOf": schemas}


def trim(v):
    if isinstance(v, list):
        return [trim(x) for x in v[:LIST_SAMPLE]]
    if isinstance(v, dict):
        return {k: trim(x) for k, x in v.items()}
    return v


def build() -> dict:
    from fastapi.testclient import TestClient

    from probate.courthouse.app import app

    spec = app.openapi()
    client = TestClient(app)
    for route, url in READS.items():
        body = client.get(url).json()
        op = spec["paths"][route]["get"]
        op["responses"]["200"]["content"]["application/json"] = {
            "schema": infer([body]),
            "example": trim(body),
        }
    spec["servers"] = [
        {
            "url": os.environ.get("PROBATE_PUBLIC_URL") or "http://localhost:8080",
            "description": "The Courthouse",
        }
    ]
    spec["components"].setdefault("securitySchemes", {})["admin"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-Probate-Admin",
        "description": "PROBATE_ADMIN_TOKEN from the Courthouse's .env",
    }
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            op["operationId"] = OPERATION_IDS[(method, path)]
        if path.startswith("/admin/"):
            for op in ops.values():
                op["security"] = [{"admin": []}]
                op["parameters"] = [
                    p for p in op.get("parameters", []) if p.get("name") != "x-probate-admin"
                ]
    return spec


def main() -> None:
    if os.environ.get("_PROBATE_SPEC_CHILD") == "1":
        print(json.dumps(build(), indent=2, ensure_ascii=False))
        return
    data = tempfile.mkdtemp(prefix="probate-spec-")
    env = {**os.environ, "PROBATE_FAKE": "1", "PROBATE_DATA_DIR": data, "PYTHONPATH": str(CORE)}
    subprocess.run(
        [sys.executable, "-m", "probate.courthouse.simulate", "--generations", "12"],
        cwd=CORE,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    out = subprocess.run(
        [sys.executable, __file__],
        cwd=CORE,
        env={**env, "_PROBATE_SPEC_CHILD": "1"},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    OUT.write_text(out, encoding="utf-8")
    spec = json.loads(out)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(spec['paths'])} paths")


if __name__ == "__main__":
    main()
