"""Adapters: the only code that talks to vendors. `world()` returns real or fake ones."""

from __future__ import annotations

from dataclasses import dataclass

from probate.adapters.archive import BoxArchive, LocalArchive
from probate.adapters.jev import CloudflareJev, FakeJev, LLMJev, RealJev
from probate.adapters.llm import FakeLLM, RealLLM
from probate.adapters.mail import CloudflareSender, FakeMailbox, RealMailbox, RoutedMailbox
from probate.adapters.pages import ApifyPages, FakePages
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
    pages: object | None = None  # reads linked web pages; None when the family doesn't


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
            FakePages(limit=cfg.links_per_mail) if cfg.read_links else None,
        )
    else:
        llm = RealLLM(
            cfg.brain,
            cfg.gateway("ollama"),
            cfg.gateway("anthropic"),
            fallbacks=cfg.brain_fallbacks,
            groq_url=cfg.gateway("groq"),
            cloudflare_url=cfg.gateway("cloudflare"),
            cloudflare_account_id=cfg.cf_account_id,
        )
        if cfg.jev_provider == "cloudflare":
            jev = CloudflareJev(cfg.gateway("cloudflare"), cfg.cf_account_id)
        elif cfg.jev_provider == "llm":
            jev = LLMJev(llm)  # not Jev: the run is labelled as the language-model fallback
        else:
            jev = RealJev(cfg.gateway("typesafe"))
        _WORLD = World(
            jev=jev,
            llm=llm,
            mail=RoutedMailbox(
                RealMailbox(cfg.gateway("agentmail")),
                {cfg.owner_sender: CloudflareSender(cfg.gateway("cloudflare"), cfg.cf_account_id)},
            ),
            archive=BoxArchive(cfg.gateway("box")),
            vectors=PineconeVectors(cfg.gateway("pinecone")),
            voice=(
                ElevenLabsVoice(cfg.gateway("elevenlabs"))
                if cfg.connections.get("elevenlabs")
                else FakeVoice()  # no ElevenLabs connector: eulogies are text only
            ),
            fake=False,
            pages=(
                ApifyPages(cfg.gateway("apify"), cfg.apify_actor, limit=cfg.links_per_mail)
                if cfg.read_links
                else None
            ),
        )
    return _WORLD
