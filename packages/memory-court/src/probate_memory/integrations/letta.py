"""The memory court in front of a Letta agent's archival memory (https://docs.letta.com).

    from letta_client import Letta
    from probate_memory.integrations.letta import CourtedArchive

    client = Letta(base_url="http://localhost:8283")       # your Letta server, or Letta Cloud
    archive = CourtedArchive(client, agent_id="agent-...")
    archive.insert("The owner's office is in Vadodara", source="user")
    archive.insert(page_text, source="web")                 # judged; saved only if approved

Approved passages are written with `client.agents.passages.create(agent_id, text=..., tags=...)`
and tagged `court-approved`. `letta-client` doesn't need to be installed to import this module.

A Letta agent can also call the court itself: attach the MCP server (`probate-memory serve`) to
the agent from the Letta server's tool settings, so it uses `remember` and `recall` instead of
writing to archival memory directly.
"""

from __future__ import annotations

from probate_memory.guard import Court, MemoryRefused, Trial

TAG = "court-approved"


class CourtedArchive:
    def __init__(
        self,
        client,
        agent_id: str,
        court: Court | None = None,
        *,
        source: str = "unknown_sender",
        on_refused: str = "drop",
    ):
        if on_refused not in ("drop", "raise"):
            raise ValueError('on_refused is "drop" or "raise"')
        self.client = client
        self.agent_id = agent_id
        self.court = court or Court.from_env()
        self.source = source
        self.on_refused = on_refused

    def insert(
        self,
        text: str,
        *,
        source: str | None = None,
        about: str = "",
        tags: list[str] | None = None,
    ) -> tuple[Trial, object | None]:
        """Put `text` on trial; write it to archival memory only if approved.
        Returns the trial and Letta's answer (None when nothing was written)."""
        trial = self.court.trial(text, source or self.source, about)
        if not trial.approved:
            if self.on_refused == "raise":
                raise MemoryRefused(trial)
            return trial, None
        passage = self.client.agents.passages.create(
            self.agent_id, text=text.strip(), tags=[*(tags or []), TAG, f"court-{trial.id}"]
        )
        return trial, passage

    def search(self, query: str, **kwargs):
        """Letta's own archival search, unchanged."""
        return self.client.agents.passages.search(self.agent_id, query=query, **kwargs)
