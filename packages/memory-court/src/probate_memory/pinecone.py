"""Optional recall by meaning: approved memories, and only approved memories, in a Pinecone index.

A memory reaches the index only after the court approves it (or the owner does), and leaves it when
it is forgotten, so nothing convicted or waiting can ever be recalled. If Pinecone is unreachable,
recall falls back to the local word search; the court and the SQLite record never depend on it.

Turn it on with PINECONE_API_KEY and PROBATE_MEMORY_PINECONE_HOST, the index host from the
Pinecone console. The index needs integrated embedding with its text field mapped to `chunk_text`
(for example `pc index create -n memory-court -m cosine -c aws -r us-east-1
--model llama-text-embed-v2 --field_map text=chunk_text`).

    upsert  POST {host}/records/namespaces/{ns}/upsert   (NDJSON: {"_id", "chunk_text", ...})
    search  POST {host}/records/namespaces/{ns}/search   {"query": {"inputs": {"text"}, "top_k"}}
    delete  POST {host}/vectors/delete                   {"ids": [...], "namespace": ns}
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_VERSION = "2025-04"  # VERIFY against the account's index on first use


class VectorsUnavailable(RuntimeError):
    """Pinecone couldn't be reached. Recall falls back to word search."""


class PineconeRecall:
    def __init__(
        self, host: str, api_key: str, namespace: str = "memory-court", timeout: float = 15
    ):
        host = host.rstrip("/")
        self.host = host if host.startswith("http") else f"https://{host}"
        self.api_key = api_key
        self.namespace = namespace
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> PineconeRecall | None:
        key = os.environ.get("PINECONE_API_KEY", "")
        host = os.environ.get("PROBATE_MEMORY_PINECONE_HOST", "")
        if not (key and host):
            return None
        return cls(host, key, os.environ.get("PROBATE_MEMORY_PINECONE_NAMESPACE", "memory-court"))

    def _post(self, path: str, body: bytes, content_type: str = "application/json") -> dict:
        req = urllib.request.Request(
            f"{self.host}{path}",
            data=body,
            headers={
                "Api-Key": self.api_key,
                "Content-Type": content_type,
                "X-Pinecone-API-Version": API_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as exc:
            raise VectorsUnavailable(f"Pinecone returned {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise VectorsUnavailable(str(exc)) from exc
        try:
            return json.loads(raw) if raw.strip() else {}
        except ValueError as exc:
            raise VectorsUnavailable("Pinecone's answer wasn't JSON") from exc

    def upsert(self, mid: int, text: str, about: str, source: str) -> None:
        record = {"_id": str(mid), "chunk_text": f"{text}\n{about}".strip(), "source": source}
        self._post(
            f"/records/namespaces/{self.namespace}/upsert",
            (json.dumps(record) + "\n").encode(),
            "application/x-ndjson",
        )

    def delete(self, mid: int) -> None:
        self._post(
            "/vectors/delete", json.dumps({"ids": [str(mid)], "namespace": self.namespace}).encode()
        )

    def search(self, query: str, limit: int) -> list[tuple[int, float]]:
        body = {"query": {"inputs": {"text": query}, "top_k": limit}, "fields": ["source"]}
        data = self._post(f"/records/namespaces/{self.namespace}/search", json.dumps(body).encode())
        hits = (data.get("result") or {}).get("hits") or []
        out = []
        for h in hits:
            try:
                out.append((int(h["_id"]), round(float(h.get("_score", 0.0)), 3)))
            except (KeyError, TypeError, ValueError):
                continue
        return out
