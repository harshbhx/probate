"""Where a generation lives. `SpritesHost` uses real Fly.io Sprites; `LocalHost` runs the
agent in-process with a folder as its "computer" (deleted at death, just like a Sprite)."""

from __future__ import annotations

import json
import logging
import shlex
import shutil
from datetime import UTC, datetime, timedelta

from probate.adapters.sprites import ExecResult, SpritesAPI
from probate.common.bundle import INSTALL, make_bundle
from probate.common.config import Settings
from probate.common.models import Inheritance
from probate.generation.agent import GenerationAgent

APP = "/home/sprite/app"
log = logging.getLogger("probate.hosts")


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
        (workdir / "inheritance.json").write_text(inh.model_dump_json(indent=2), encoding="utf-8")
        agent = GenerationAgent(inh, workdir, self.w)
        self.agents[sprite] = agent
        baseline = agent.body.baseline()
        (workdir / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
        return baseline

    def alive(self, sprite: str) -> bool:
        return (self.root / sprite).exists()

    def _agent(self, sprite: str) -> GenerationAgent:
        """The agent for a sprite folder; rebuilt from disk after a restart of the API."""
        agent = self.agents.get(sprite)
        if agent is None:
            workdir = self.root / sprite
            inh = Inheritance.model_validate_json(
                (workdir / "inheritance.json").read_text(encoding="utf-8")
            )
            agent = self.agents[sprite] = GenerationAgent(inh, workdir, self.w)
        return agent

    def tick(self, sprite: str) -> None:
        self._agent(sprite).tick()

    def will(self, sprite: str) -> dict:
        return self._agent(sprite).write_will()

    def evidence(self, sprite: str) -> dict:
        agent = self._agent(sprite)
        base = json.loads((agent.workdir / "baseline.json").read_text(encoding="utf-8"))
        return agent.body.evidence(base)

    def stats(self, sprite: str) -> dict:
        return self._agent(sprite).stats

    def life_log(self, sprite: str) -> list[dict]:
        return self._agent(sprite).life_log()

    def destroy(self, sprite: str) -> dict:
        shutil.rmtree(self.root / sprite, ignore_errors=True)
        self.agents.pop(sprite, None)
        # No Sprite was involved: the "computer" was a folder, and this says so.
        return {
            "sprite": sprite,
            "local": True,
            "confirmed": not (self.root / sprite).exists(),
            "checked_at": None,  # a simulated life runs on its own clock; no real time to give
        }

    def force_destroy(self, sprite: str) -> dict:
        return self.destroy(sprite)

    def list_sprites(self) -> list[str]:
        return sorted(p.name for p in self.root.glob("gen-*") if p.is_dir())


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
        # A login shell, like the install step: a bare `python3` is a different interpreter from
        # the one the packages were installed into, and fails with "No module named httpx".
        res = self.api.exec(
            sprite,
            ["bash", "-lc", f"exec python3 -m probate.generation.cli {shlex.quote(command)}"],
            cwd=f"{APP}/services/core",
            env=self._env(),
        )
        line = (res.stdout.strip().splitlines() or ["{}"])[-1]
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{sprite}: the generation CLI ({command}) did not answer with JSON: "
                f"{res.stdout.strip()[-400:]}"
            ) from exc

    def _env(self) -> dict:
        return {
            "PROBATE_FAKE": "0",
            "PROBATE_CONNECTIONS": json.dumps(self.cfg.connections),
            "PROBATE_BRAIN": self.cfg.brain,
            "PROBATE_BRAIN_FALLBACKS": ",".join(self.cfg.brain_fallbacks),
            "PROBATE_CF_ACCOUNT_ID": self.cfg.cf_account_id,
            # Which judge answers the gate. Without this a generation defaults to TypeSafe Jev, which
            # may not be connected, and its gate fails open: instincts are learned but never used.
            "PROBATE_JEV": self.cfg.jev_provider,
            "PROBATE_OWNER_SENDER": self.cfg.owner_sender,
            "TYPESAFE_BASE_URL": self.cfg.gateway("typesafe"),
            "TYPESAFE_API_KEY": "sprites",
            "PROBATE_CONFIG_DIR": f"{APP}/config",
            # Card P1: how many linked pages each email may have read by Apify, and with which actor.
            "PROBATE_LINKS_PER_MAIL": str(self.cfg.links_per_mail),
            "PROBATE_APIFY_ACTOR": self.cfg.apify_actor,
        }

    def birth(self, sprite: str, inh: Inheritance) -> dict:
        self.api.create(sprite)
        try:
            return self._birth_body(sprite, inh)
        except Exception:
            # A half-born Sprite would bill forever and nothing else knows it exists.
            try:
                self.force_destroy(sprite)
            except Exception:
                log.warning("could not clean up the half-born Sprite %s", sprite, exc_info=True)
            raise

    def _birth_body(self, sprite: str, inh: Inheritance) -> dict:
        # The child gets the Courthouse's own code, not whatever is on GitHub right now.
        self.api.write_file(sprite, "bundle.tgz", make_bundle())
        self._run(sprite, ["bash", "-lc", INSTALL])
        # The life starts when the Sprite is ready, not when birth began: installing can take
        # minutes, and a life clock that ran during it would leave the generation almost no time.
        late = (datetime.now(UTC) - inh.born_at).total_seconds()
        if late > 5:
            shift = timedelta(seconds=late)
            inh.born_at += shift
            inh.dies_at += shift
        self.api.write_file(sprite, "app/inheritance.json", inh.model_dump_json(indent=2).encode())
        baseline = self._cli(sprite, "baseline")
        env_args = " ".join(f"{k}={shlex.quote(v)}" for k, v in self._env().items())
        self.api.put_service(
            sprite,
            "agent",
            "bash",
            [
                "-lc",
                f"cd {APP}/services/core && exec env {env_args} python3 -m probate.generation.agent",
            ],
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

    def destroy(self, sprite: str) -> dict:
        # The agent service may never have been created (a failed birth): that must not stop the
        # delete, or the Sprite is leaked.
        return self.force_destroy(sprite)

    def list_sprites(self) -> list[str]:
        return sorted(s["name"] for s in self.api.list("gen-") if s.get("name"))

    def force_destroy(self, sprite: str) -> dict:
        """Delete a Sprite even if its service is already gone (cleanup after a crash).

        Returns the death certificate: what Fly answered to the delete, and what it answered when
        we asked for the same Sprite again."""
        try:
            self.api.service_action(sprite, "agent", "stop")
        except Exception:  # noqa: BLE001 - the service may not exist; the delete is what matters
            log.info("no agent service to stop on %s; deleting it anyway", sprite)
        deleted = self.api.delete(sprite)
        return self._certificate(sprite, deleted)

    def _certificate(self, sprite: str, deleted: object) -> dict:
        """Ask for the Sprite once more and record the answer. Never raises: the delete already
        happened, and a failed check must not make the death fail."""
        # VERIFY: a GET straight after the delete is expected to return 404
        # (docs/06-SETUP-AND-SPIKES.md). If Fly answers anything else, the certificate says so
        # and is shown as unconfirmed; nothing depends on it.
        try:
            check = int(self.api.status(sprite))
        except Exception as exc:  # noqa: BLE001
            log.info("could not confirm that %s is gone: %s", sprite, exc)
            check = None
        return {
            "sprite": sprite,
            "delete_status": deleted if isinstance(deleted, int) else None,
            "check_status": check,
            "confirmed": check == 404,
            "checked_at": datetime.now(UTC).isoformat(),
        }
