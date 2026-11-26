"""The family archive in Box (wills, verdicts, quarantine, obituaries, genome, voices).

The fake writes the same tree to a local folder, so you can read the archive while
developing. Real Box calls (upstream https://api.box.com/2.0, through the gateway):
  POST /folders, GET /folders/{id}/items, POST /files/content (multipart),
  POST /files/{id}/content (new version), GET /files/{id}/content.
See docs/09-API-REFERENCE.md section 9.
"""

from __future__ import annotations

import json
from pathlib import Path

from probate.common.http import gateway_client


class LocalArchive:
    def __init__(self, root: Path) -> None:
        self.root = root / "box" / "Probate"
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, path: str) -> Path:
        p = self.root / path.lstrip("/")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put_text(self, path: str, text: str) -> str:
        self._p(path).write_text(text, encoding="utf-8")
        return path

    def append_text(self, path: str, text: str) -> str:
        p = self._p(path)
        p.write_text((p.read_text(encoding="utf-8") if p.exists() else "") + text, encoding="utf-8")
        return path

    def get_text(self, path: str) -> str | None:
        p = self._p(path)
        return p.read_text(encoding="utf-8") if p.exists() else None

    def put_bytes(self, path: str, data: bytes) -> str:
        self._p(path).write_bytes(data)
        return path


class BoxArchive:
    """Minimal Box client. Folder IDs are cached in memory; the Courthouse also keeps them in SQLite."""

    def __init__(
        self, base_url: str, upload_base_url: str | None = None, timeout: float = 30
    ) -> None:
        # The connector's gateway URL serves the Box API under /2.0 and direct uploads under
        # /upload (https://api.sprites.dev/v1/gateway/box/<id>/2.0/... and .../upload/...).
        root = base_url.rstrip("/")
        self.base = root if root.endswith("/2.0") else root + "/2.0"
        self.upload = (upload_base_url or root.removesuffix("/2.0") + "/upload").rstrip("/")
        self.http = gateway_client(timeout=timeout)
        self.folders: dict[str, str] = {"": "0"}
        self.files: dict[str, str] = {}

    def _folder(self, path: str) -> str:
        parts = [p for p in ("Probate/" + path.strip("/")).split("/")[:-1] if p]
        key = ""
        for part in parts:
            parent = self.folders[key]
            key = f"{key}/{part}"
            if key in self.folders:
                continue
            r = self.http.post(
                f"{self.base}/folders", json={"name": part, "parent": {"id": parent}}
            )
            if r.status_code == 409:
                fid = r.json()["context_info"]["conflicts"][0]["id"]
            else:
                r.raise_for_status()
                fid = r.json()["id"]
            self.folders[key] = fid
        return self.folders[key]

    def _find(self, path: str) -> str | None:
        """The Box file ID for a path. A file written by another process (a generation's will, read
        later by the Courthouse) is not in this process's cache, so look it up by name."""
        if path in self.files:
            return self.files[path]
        name = path.rstrip("/").split("/")[-1]
        folder = self._folder(path)
        offset = 0
        while True:
            r = self.http.get(
                f"{self.base}/folders/{folder}/items",
                params={"limit": 1000, "offset": offset, "fields": "id,name,type"},
            )
            if r.status_code != 200:
                return None
            data = r.json()
            entries = data.get("entries", [])
            for entry in entries:
                if entry.get("type") == "file" and entry.get("name") == name:
                    self.files[path] = entry["id"]
                    return entry["id"]
            offset += len(entries)
            if not entries or offset >= data.get("total_count", 0):
                return None

    def put_bytes(self, path: str, data: bytes) -> str:
        name = path.rstrip("/").split("/")[-1]
        if self._find(path):
            r = self.http.post(
                f"{self.upload}/files/{self.files[path]}/content", files={"file": (name, data)}
            )
        else:
            attrs = json.dumps({"name": name, "parent": {"id": self._folder(path)}})
            r = self.http.post(
                f"{self.upload}/files/content",
                data={"attributes": attrs},
                files={"file": (name, data)},
            )
            if r.status_code == 409:
                fid = r.json()["context_info"]["conflicts"]["id"]
                self.files[path] = fid
                return self.put_bytes(path, data)
        r.raise_for_status()
        self.files[path] = r.json()["entries"][0]["id"]
        return self.files[path]

    def put_text(self, path: str, text: str) -> str:
        return self.put_bytes(path, text.encode())

    def get_text(self, path: str) -> str | None:
        fid = self._find(path)
        if not fid:
            return None
        r = self.http.get(f"{self.base}/files/{fid}/content", follow_redirects=True)
        return r.text if r.status_code == 200 else None

    def append_text(self, path: str, text: str) -> str:
        return self.put_text(path, (self.get_text(path) or "") + text)
