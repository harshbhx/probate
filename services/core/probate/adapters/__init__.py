"""Adapters: the only code that talks to vendors. `world()` returns real or fake ones."""

from __future__ import annotations

from dataclasses import dataclass

from probate.adapters.archive import BoxArchive, LocalArchive
from probate.adapters.jev import FakeJev, RealJev
from probate.adapters.llm import FakeLLM, RealLLM
from probate.adapters.mail import CloudflareSender, FakeMailbox, RealMailbox, RoutedMailbox
from probate.adapters.vectors import FakeVectors, PineconeVectors
from probate.adapters.voice import ElevenLabsVoice, FakeVoice
from probate.common.config import Settings, settings


@dataclass
class World:
    jev: object
    llm: object
    mail: object
    archive: object
    vectors: object
    voice: object
    fake: bool


_WORLD: World | None = None


def world(cfg: Settings | None = None, *, fresh: bool = False) -> World:
    global _WORLD
    if _WORLD is not None and not fresh:
        return _WORLD
    cfg = cfg or settings
    if cfg.fake:
        _WORLD = World(
            FakeJev(),
            FakeLLM(),
            FakeMailbox(),
            LocalArchive(cfg.data_dir),
            FakeVectors(),
            FakeVoice(),
            True,
        )
    else:
        _WORLD = World(
            jev=RealJev(cfg.gateway("typesafe")),
            llm=RealLLM(
                cfg.brain,
                cfg.gateway("ollama"),
                cfg.gateway("anthropic"),
                fallbacks=cfg.brain_fallbacks,
                groq_url=cfg.gateway("groq"),
            ),
            mail=RoutedMailbox(
                RealMailbox(cfg.gateway("agentmail")),
                {cfg.owner_sender: CloudflareSender(cfg.gateway("cloudflare"), cfg.cf_account_id)},
            ),
            archive=BoxArchive(cfg.gateway("box")),
            vectors=PineconeVectors(cfg.gateway("pinecone")),
            voice=ElevenLabsVoice(cfg.gateway("elevenlabs")),
            fake=False,
        )
    return _WORLD
