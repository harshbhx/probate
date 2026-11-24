"""Ancestral memory in Pinecone (integrated-embedding index, records API).

Real: POST /records/namespaces/{ns}/upsert (NDJSON) and POST /records/namespaces/{ns}/search,
header X-Pinecone-Api-Version. See docs/09-API-REFERENCE.md section 5.
"""

from __future__ import annotations

import json
import re

import httpx

from probate.common.models import MemoryItem

API_VERSION = "2026-04"


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]{3,}", text.lower())}


class FakeVectors:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def upsert(self, items: list[MemoryItem], namespace: str = "family") -> None:
        ids = {r["_id"] for r in self.records}
        for it in items:
            if it.id not in ids:
                self.records.append(
                    {
                        "_id": it.id,
                        "chunk_text": it.text,
                        "gen": it.gen,
                        "category": it.category.value,
                    }
                )

    def search(self, text: str, k: int = 5, namespace: str = "family") -> list[dict]:
        q = _words(text)
        scored = sorted(self.records, key=lambda r: -len(q & _words(r["chunk_text"])))
        return [r for r in scored[:k] if q & _words(r["chunk_text"])]


class PineconeVectors:
    def __init__(self, base_url: str, timeout: float = 20) -> None:
        self.base = base_url.rstrip("/")  # VERIFY in spike S7: gateway path to the index host
        self.http = httpx.Client(timeout=timeout, headers={"X-Pinecone-Api-Version": API_VERSION})

    def upsert(self, items: list[MemoryItem], namespace: str = "family") -> None:
        if not items:
            return
        lines = "\n".join(
            json.dumps(
                {
                    "_id": it.id,
                    "chunk_text": it.text,
                    "gen": it.gen,
                    "category": it.category.value,
                    "source": it.source.value,
                }
            )
            for it in items
        )
        r = self.http.post(
            f"{self.base}/records/namespaces/{namespace}/upsert",
            content=lines,
            headers={"Content-Type": "application/x-ndjson"},
        )
        r.raise_for_status()

    def search(self, text: str, k: int = 5, namespace: str = "family") -> list[dict]:
        body = {
            "query": {"inputs": {"text": text}, "top_k": k},
            "fields": ["chunk_text", "gen", "category"],
        }
        r = self.http.post(f"{self.base}/records/namespaces/{namespace}/search", json=body)
        if r.status_code != 200:
            return []
        hits = r.json().get("result", {}).get("hits", [])
        return [{"_id": h.get("_id"), **h.get("fields", {})} for h in hits]
