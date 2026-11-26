"""Fly.io Sprites REST client (Courthouse only).

Base https://api.sprites.dev/v1, Authorization: Bearer <token>. Endpoints from the Sprites
OpenAPI spec (docs/09-API-REFERENCE.md section 1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from probate.common.http import gateway_client

API = "https://api.sprites.dev/v1"


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


def parse_frames(raw: bytes) -> ExecResult | None:
    """Decode the exec stream: marker byte 1 = stdout, 2 = stderr, 3 = exit (the next byte is the
    exit code). Returns None when the body is not framed, so the caller can try other formats."""
    if not raw or raw[0] not in (1, 2, 3):
        return None
    out: list[bytes] = []
    err: list[bytes] = []
    code = 0
    i = 0
    while i < len(raw):
        marker = raw[i]
        if marker == 3:
            code = raw[i + 1] if i + 1 < len(raw) else 0
            i += 2
            continue
        if marker not in (1, 2):
            return None
        j = i + 1
        while j < len(raw) and raw[j] not in (1, 2, 3):
            j += 1
        (out if marker == 1 else err).append(raw[i + 1 : j])
        i = j
    return ExecResult(
        code, b"".join(out).decode(errors="replace"), b"".join(err).decode(errors="replace")
    )


class SpritesAPI:
    def __init__(self, token: str, base: str = API, timeout: float = 180) -> None:
        self.base = base.rstrip("/")
        self.http = gateway_client(
            retry_all=True,  # every call here (exec, files, services) is safe to repeat
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"},
        )

    # Sprites
    def create(self, name: str, public: bool = False) -> dict:
        r = self.http.post(
            f"{self.base}/sprites",
            json={"name": name, "url_settings": {"auth": "public" if public else "sprite"}},
        )
        if r.status_code == 409:
            return self.get(name)
        r.raise_for_status()
        return r.json()

    def get(self, name: str) -> dict | None:
        r = self.http.get(f"{self.base}/sprites/{name}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def list(self, prefix: str = "gen-") -> list[dict]:
        r = self.http.get(f"{self.base}/sprites", params={"prefix": prefix, "max_results": 100})
        r.raise_for_status()
        return r.json().get("sprites", [])

    def delete(self, name: str) -> None:
        r = self.http.delete(f"{self.base}/sprites/{name}")
        if r.status_code not in (200, 202, 204, 404):
            r.raise_for_status()

    def make_public(self, name: str) -> dict:
        r = self.http.put(f"{self.base}/sprites/{name}", json={"url_settings": {"auth": "public"}})
        r.raise_for_status()
        return r.json()

    # Exec and files
    def exec(
        self,
        name: str,
        argv: list[str],
        *,
        cwd: str = "/home/sprite/app",
        env: dict | None = None,
        stdin: bytes | None = None,
    ) -> ExecResult:
        params: list[tuple[str, str]] = [("cmd", a) for a in argv] + [("dir", cwd)]
        params += [("env", f"{k}={v}") for k, v in (env or {}).items()]
        if stdin is not None:
            params.append(("stdin", "true"))
        r = self.http.post(f"{self.base}/sprites/{name}/exec", params=params, content=stdin or b"")
        r.raise_for_status()
        framed = parse_frames(r.content)
        if framed is not None:
            return framed
        # Older or other responses: JSON {exit_code, stdout, stderr}, or plain stdout.
        try:
            data = r.json()
            return ExecResult(
                int(data.get("exit_code", 0)), data.get("stdout", ""), data.get("stderr", "")
            )
        except (json.JSONDecodeError, ValueError):
            return ExecResult(0, r.text, "")

    def write_file(self, name: str, path: str, data: bytes, mode: str = "0644") -> None:
        r = self.http.put(
            f"{self.base}/sprites/{name}/fs/write",
            params={"path": path, "workingDir": "/home/sprite", "mkdir": "true", "mode": mode},
            content=data,
        )
        r.raise_for_status()

    def read_file(self, name: str, path: str) -> bytes | None:
        r = self.http.get(
            f"{self.base}/sprites/{name}/fs/read",
            params={"path": path, "workingDir": "/home/sprite"},
        )
        return r.content if r.status_code == 200 else None

    # Services
    def put_service(
        self, name: str, service: str, cmd: str, args: list[str], http_port: int | None = None
    ) -> None:
        r = self.http.put(
            f"{self.base}/sprites/{name}/services/{service}",
            json={"cmd": cmd, "args": args, "needs": [], "http_port": http_port},
        )
        r.raise_for_status()

    def service_action(self, name: str, service: str, action: str) -> None:
        r = self.http.post(f"{self.base}/sprites/{name}/services/{service}/{action}")
        if r.status_code not in (200, 202, 204, 404):
            r.raise_for_status()
