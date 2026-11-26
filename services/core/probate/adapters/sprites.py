"""Fly.io Sprites REST client (Courthouse only).

Base https://api.sprites.dev/v1, Authorization: Bearer <token>. Endpoints from the Sprites
OpenAPI spec (docs/09-API-REFERENCE.md section 1).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

API = "https://api.sprites.dev/v1"


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


class SpritesAPI:
    def __init__(self, token: str, base: str = API, timeout: float = 180) -> None:
        self.base = base.rstrip("/")
        self.http = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"},
            transport=httpx.HTTPTransport(retries=3),  # a dropped TLS handshake is retried
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
        # VERIFY in spike S2: response format. Accept JSON {exit_code, stdout, stderr} or raw stdout.
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
