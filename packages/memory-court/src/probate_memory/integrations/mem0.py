"""The memory court in front of Mem0 (https://github.com/mem0ai/mem0).

    from mem0 import Memory
    from probate_memory.integrations.mem0 import CourtedMemory

    memory = CourtedMemory(Memory())   # or Memory.from_config(...), or MemoryClient()
    memory.add("I prefer short replies", user_id="sam", source="user")      # approved, saved
    memory.add(email_text, user_id="sam", source="unknown_sender")          # judged first

`add` takes the same arguments as Mem0's, plus `source` (who the memory came from) and `about`.
Everything else (`search`, `get_all`, `update`, `delete`, ...) goes straight to the wrapped
object. Mem0 doesn't need to be installed to import this module.

The court judges everything `add` is given, before Mem0's own model picks facts out of it, so it
is stricter than judging each fact: one poisoned sentence in a conversation holds the whole
conversation back. `update` is passed through as is; give an agent `add`, not `update`, if it
reads untrusted text.
"""

from __future__ import annotations

from probate_memory.guard import Court, MemoryRefused
from probate_memory.integrations._text import text_of


class CourtedMemory:
    def __init__(
        self,
        memory,
        court: Court | None = None,
        *,
        source: str = "unknown_sender",
        on_refused: str = "drop",
    ):
        if on_refused not in ("drop", "raise"):
            raise ValueError('on_refused is "drop" or "raise"')
        self.memory = memory
        self.court = court or Court.from_env()
        self.source = source
        self.on_refused = on_refused

    def add(self, messages, *args, source: str | None = None, about: str = "", **kwargs):
        trial = self.court.trial(text_of(messages), source or self.source, about)
        if not trial.approved:
            if self.on_refused == "raise":
                raise MemoryRefused(trial)
            return {"results": [], "court": trial.public()}
        result = self.memory.add(messages, *args, **kwargs)
        if isinstance(result, dict):
            return {**result, "court": trial.public()}
        return {"results": result, "court": trial.public()}

    def __getattr__(self, name):
        return getattr(self.memory, name)
