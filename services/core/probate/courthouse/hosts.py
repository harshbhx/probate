"""Where a generation lives. `SpritesHost` uses real Fly.io Sprites; `LocalHost` runs the
agent in-process with a folder as its "computer" (deleted at death, just like a Sprite)."""

from __future__ import annotations

import json
import logging
import shlex
import shutil
import time
from datetime import UTC, datetime, timedelta

from probate.adapters.sprites import ExecResult, ForeignSprite, SpriteExists, SpritesAPI
from probate.common.bundle import INSTALL, make_bundle
from probate.common.config import Settings
from probate.common.models import Inheritance
from probate.generation.agent import GenerationAgent

APP = "/home/sprite/app"
log = logging.getLogger("probate.hosts")
# The agent polls every 20 s; a loop silent this long has stopped and is restarted.
STALE_LOOP_SECONDS = 150
# An agent whose loop has never gone round once is given this long, not 150 s: staging lives are
# 120 s, and a first life whose agent never started would be over before the watchdog looked.
FIRST_BEAT_SECONDS = 60
RESTART_EVERY_SECONDS = 300


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

    owns = None

    def __init__(self, cfg: Settings, w, owns=None) -> None:
        # owns(name): does a row of this Courthouse's database own that Sprite name?
        self.owns = owns
        self.api = SpritesAPI(cfg.sprites_token)
        self.cfg = cfg
        self.w = w
        self._restarted: dict[str, float] = {}  # sprite -> monotonic time of the last restart

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
        try:
            self.api.create(sprite, adopt=False)
        except SpriteExists:
            # Sprite names carry no environment. A name this database does not own belongs to
            # another environment's live Sprite: fail, never adopt, install over or delete it.
            if not (self.owns and self.owns(sprite)):
                raise ForeignSprite(
                    f"The Sprite name {sprite} is already taken by a Sprite this Courthouse did "
                    "not create (another environment in the same Sprites organization?). The "
                    "birth was refused and that Sprite was left alone. Production and the judges "
                    "demo must never run at the same time (docs/13-RUNBOOK.md)."
                ) from None
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
        self.api.write_file(sprite, "bundle.tgz", make_bundle(redact_owner=True))
        self._run(sprite, ["bash", "-lc", INSTALL])
        # The life starts when the Sprite is ready, not when birth began: installing can take
        # minutes, and a life clock that ran during it would leave the generation almost no time.
        late = (datetime.now(UTC) - inh.born_at).total_seconds()
        if late > 5:
            shift = timedelta(seconds=late)
            inh.born_at += shift
            inh.dies_at += shift
        # The generation only needs to know who the owner is; payment destinations stay with the court.
        safe = inh.model_copy(
            update={"owner": inh.owner.model_copy(update={"payment_destinations": []})}
        )
        self.api.write_file(sprite, "app/inheritance.json", safe.model_dump_json(indent=2).encode())
        baseline = self._cli(sprite, "baseline")
        self._register_agent(sprite)
        self.api.service_action(sprite, "agent", "start")
        return baseline

    def _register_agent(self, sprite: str) -> None:
        """(Re)define the agent service. Idempotent: a restart of a service that was never created
        would otherwise be a 404 that the API client ignores, and the agent would never run."""
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

    def restart_agent(self, sprite: str) -> None:
        """Restart the agent; if its service was never created or never started, create and start
        it. Covers a birth that was cut short as well as a loop that stopped."""
        self._register_agent(sprite)
        self.api.service_action(sprite, "agent", "restart")
        try:
            self.api.service_action(sprite, "agent", "start")  # for a restart that did not start it
        except Exception:  # noqa: BLE001 - already running is fine
            log.info("%s: agent start after restart was refused (already running?)", sprite)

    def alive(self, sprite: str) -> bool:
        return self.api.get(sprite) is not None

    def tick(self, sprite: str) -> dict:
        """Health check that also keeps the Sprite awake. An agent loop that has not gone round
        for STALE_LOOP_SECONDS, or that never went round once in FIRST_BEAT_SECONDS, is restarted
        (at most every RESTART_EVERY_SECONDS)."""
        st = self._cli(sprite, "status")
        age = st.get("loop_age") if isinstance(st, dict) else None
        now = time.monotonic()
        never_started = isinstance(st, dict) and st.get("loop_beat") is False
        limit = FIRST_BEAT_SECONDS if never_started else STALE_LOOP_SECONDS
        if (
            isinstance(age, (int, float))
            and age > limit
            and now - self._restarted.get(sprite, -1e9) > RESTART_EVERY_SECONDS
        ):
            self._restarted[sprite] = now
            log.warning(
                "%s: agent loop silent for %s s (never started: %s); restarting",
                sprite,
                age,
                never_started,
            )
            self.restart_agent(sprite)
            st["restarted"] = True
        return st

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
        # A GET straight after the delete returns 404: confirmed in the real run on 26 Nov 2026
        # (8 of 8 deaths, generations 11 to 18). If Fly ever answers anything else, the
        # certificate says so and is shown as unconfirmed; nothing depends on it.
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
