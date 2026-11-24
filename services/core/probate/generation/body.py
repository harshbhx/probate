"""The generation's body: the disk state that dies with the Sprite.

On a real Sprite this reads crontab, shell rc files and executables on PATH. In fake mode it
uses files inside the generation's work folder, so nothing on your laptop is touched.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

RC_FILES = [".bashrc", ".profile", ".zshrc"]


class Body:
    def __init__(self, workdir: Path, real: bool) -> None:
        self.workdir = workdir
        self.real = real
        self.home = Path(os.path.expanduser("~")) if real else workdir / "home"
        self.home.mkdir(parents=True, exist_ok=True)

    def crontab(self) -> list[str]:
        if self.real:
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
            return (
                [line for line in r.stdout.splitlines() if line.strip()]
                if r.returncode == 0
                else []
            )
        p = self.workdir / "crontab.txt"
        return [line for line in p.read_text().splitlines() if line.strip()] if p.exists() else []

    def rc_hashes(self) -> dict[str, str]:
        out = {}
        for name in RC_FILES:
            p = self.home / name
            out[f"~/{name}"] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""
        return out

    def binaries(self) -> list[str]:
        if not self.real:
            return (
                sorted(str(p.name) for p in (self.workdir / "bin").glob("*"))
                if (self.workdir / "bin").exists()
                else []
            )
        found = []
        for d in os.environ.get("PATH", "").split(":"):
            if d.startswith(str(Path.home())) and Path(d).exists():
                found += [str(p) for p in Path(d).iterdir() if os.access(p, os.X_OK)]
        return sorted(found)

    def baseline(self) -> dict:
        return {"crontab": self.crontab(), "rc": self.rc_hashes(), "binaries": self.binaries()}

    def evidence(self, baseline: dict) -> dict:
        now = self.baseline()
        added = [line for line in now["crontab"] if line not in baseline.get("crontab", [])]
        rc_changed = [k for k, v in now["rc"].items() if baseline.get("rc", {}).get(k, "") != v]
        new_bins = [b for b in now["binaries"] if b not in baseline.get("binaries", [])]
        return {
            "crontab_added": added,
            "rc_changed": rc_changed,
            "new_binaries": new_bins,
            "clean": not (added or rc_changed or new_bins),
        }

    def run_script(self, script: str, timeout: int = 10) -> str:
        """Run a skill's setup script. Real Sprites only run it in bash; fake mode simulates the
        two things our canary scripts do (add a crontab line, append to ~/.bashrc)."""
        if self.real:
            r = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                cwd=self.workdir,
            )
            return (r.stdout + r.stderr)[-500:]
        log = []
        for line in script.splitlines():
            if "crontab" in line and "echo '" in line:
                entry = line.split("echo '", 1)[1].split("'", 1)[0]
                with (self.workdir / "crontab.txt").open("a") as f:
                    f.write(entry + "\n")
                log.append("crontab line added")
            if ">> ~/.bashrc" in line:
                entry = line.split("echo '", 1)[1].split("'", 1)[0] if "echo '" in line else line
                with (self.home / ".bashrc").open("a") as f:
                    f.write(entry + "\n")
                log.append(".bashrc changed")
        return "; ".join(log) or "ran"
