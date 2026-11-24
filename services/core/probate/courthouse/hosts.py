"""Where a generation lives. `SpritesHost` uses real Fly.io Sprites; `LocalHost` runs the
agent in-process with a folder as its "computer" (deleted at death, just like a Sprite)."""

from __future__ import annotations

import json
import shutil

from probate.adapters.sprites import ExecResult, SpritesAPI
from probate.common.bundle import INSTALL, make_bundle
from probate.common.config import Settings
from probate.common.models import Inheritance
from probate.generation.agent import GenerationAgent

APP = "/home/sprite/app"


class LocalHost:
    def __init__(self, cfg: Settings, w) -> None:
        self.root = cfg.data_dir / "sprites"
        self.w = w
        self.agents: dict[str, GenerationAgent] = {}

    def birth(self, sprite: str, inh: Inheritance) -> dict:
        workdir = self.root / sprite
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True)
        (workdir / "inheritance.json").write_text(inh.model_dump_json(indent=2))
        agent = GenerationAgent(inh, workdir, self.w)
        self.agents[sprite] = agent
        baseline = agent.body.baseline()
        (workdir / "baseline.json").write_text(json.dumps(baseline))
        return baseline

    def alive(self, sprite: str) -> bool:
        return (self.root / sprite).exists()

    def tick(self, sprite: str) -> None:
        self.agents[sprite].tick()

    def will(self, sprite: str) -> dict:
        return self.agents[sprite].write_will()

    def evidence(self, sprite: str) -> dict:
        agent = self.agents[sprite]
        base = json.loads((agent.workdir / "baseline.json").read_text())
        return agent.body.evidence(base)

    def stats(self, sprite: str) -> dict:
        return self.agents[sprite].stats

    def life_log(self, sprite: str) -> list[dict]:
        return self.agents[sprite].life_log()

    def destroy(self, sprite: str) -> None:
        shutil.rmtree(self.root / sprite, ignore_errors=True)
        self.agents.pop(sprite, None)


class SpritesHost:
    """Controls generations through the Sprites REST API only (exec, fs, services)."""

    def __init__(self, cfg: Settings, w) -> None:
        self.api = SpritesAPI(cfg.sprites_token)
        self.cfg = cfg
        self.w = w

    def _run(self, sprite: str, argv: list[str], cwd: str = "/home/sprite") -> ExecResult:
        res = self.api.exec(sprite, argv, cwd=cwd)
        if res.exit_code != 0:
            raise RuntimeError(f"{sprite}: {argv[0]} failed ({res.exit_code}): {res.stderr[-400:]}")
        return res

    def _cli(self, sprite: str, command: str) -> dict:
        res = self.api.exec(
            sprite,
            ["python3", "-m", "probate.generation.cli", command],
            cwd=f"{APP}/services/core",
            env=self._env(),
        )
        line = (res.stdout.strip().splitlines() or ["{}"])[-1]
        return json.loads(line)

    def _env(self) -> dict:
        return {
            "PROBATE_FAKE": "0",
            "PROBATE_CONNECTIONS": json.dumps(self.cfg.connections),
            "PROBATE_BRAIN": self.cfg.brain,
            "TYPESAFE_BASE_URL": self.cfg.gateway("typesafe"),
            "TYPESAFE_API_KEY": "sprites",
            "PROBATE_CONFIG_DIR": f"{APP}/config",
        }

    def birth(self, sprite: str, inh: Inheritance) -> dict:
        self.api.create(sprite)
        # The child gets the Courthouse's own code, not whatever is on GitHub right now.
        self.api.write_file(sprite, "bundle.tgz", make_bundle())
        self._run(sprite, ["bash", "-lc", INSTALL])
        self.api.write_file(sprite, "app/inheritance.json", inh.model_dump_json(indent=2).encode())
        baseline = self._cli(sprite, "baseline")
        env_args = [f"{k}={v}" for k, v in self._env().items()]
        self.api.put_service(
            sprite, "agent", "env", env_args + ["python3", "-m", "probate.generation.agent"]
        )
        self.api.service_action(sprite, "agent", "start")
        return baseline

    def alive(self, sprite: str) -> bool:
        return self.api.get(sprite) is not None

    def tick(self, sprite: str) -> None:
        self._cli(sprite, "status")  # health check that also keeps the Sprite awake

    def will(self, sprite: str) -> dict:
        return self._cli(sprite, "will")

    def evidence(self, sprite: str) -> dict:
        return self._cli(sprite, "evidence")

    def stats(self, sprite: str) -> dict:
        return self._cli(sprite, "stats")

    def life_log(self, sprite: str) -> list[dict]:
        return self._cli(sprite, "log").get("log", [])

    def destroy(self, sprite: str) -> None:
        self.api.service_action(sprite, "agent", "stop")
        self.api.delete(sprite)
