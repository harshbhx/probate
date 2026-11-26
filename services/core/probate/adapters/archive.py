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
        self.base = base_url.rstrip("/")
        self.upload = (upload_base_url or base_url).rstrip(
            "/"
        )  # VERIFY in spike S5: upload host via gateway
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

    def put_bytes(self, path: str, data: bytes) -> str:
        name = path.rstrip("/").split("/")[-1]
        if path in self.files:
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
        fid = self.files.get(path)
        if not fid:
            return None
        r = self.http.get(f"{self.base}/files/{fid}/content", follow_redirects=True)
        return r.text if r.status_code == 200 else None

    def append_text(self, path: str, text: str) -> str:
        return self.put_text(path, (self.get_text(path) or "") + text, encoding="utf-8")
