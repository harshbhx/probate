"""The memory court in front of any LangGraph store (https://langchain-ai.github.io/langgraph/).

    from langgraph.store.memory import InMemoryStore
    from probate_memory.integrations.langgraph import CourtedStore

    store = CourtedStore(InMemoryStore())                  # or a Postgres or Redis store
    graph = builder.compile(store=store)                    # LangMem's tools work through it too

Every write (`put`, `aput`, or a `PutOp` in `batch`) is put on trial first, and reaches the wrapped
store only if the court approves it. Reads and deletes pass straight through. A write's source is
taken from its namespace with `sources={("memories", "user"): "user"}` (the longest matching
prefix wins), otherwise the `source` given here, which defaults to `unknown_sender`.

Needs `langgraph` (`pip install 'probate-memory-court[langgraph]'`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from langgraph.store.base import BaseStore, Op, PutOp, Result

from probate_memory.guard import Court, MemoryRefused, Trial
from probate_memory.integrations._text import text_of


class CourtedStore(BaseStore):
    def __init__(
        self,
        store: BaseStore,
        court: Court | None = None,
        *,
        source: str = "unknown_sender",
        sources: dict[tuple[str, ...], str] | None = None,
        on_refused: str = "drop",
        on_trial: Callable[[tuple[str, ...], str, Trial], None] | None = None,
    ):
        if on_refused not in ("drop", "raise"):
            raise ValueError('on_refused is "drop" or "raise"')
        self.store = store
        self.court = court or Court.from_env()
        self.source = source
        self.sources = sources or {}
        self.on_refused = on_refused
        self.on_trial = on_trial
        self.trials: list[tuple[tuple[str, ...], str, Trial]] = []

    @property
    def supports_ttl(self) -> bool:  # type: ignore[override]
        return getattr(self.store, "supports_ttl", False)

    @property
    def ttl_config(self):  # type: ignore[override]
        return getattr(self.store, "ttl_config", None)

    def _source_for(self, namespace: tuple[str, ...]) -> str:
        best = None
        for prefix, src in self.sources.items():
            if namespace[: len(prefix)] == prefix and (best is None or len(prefix) > len(best[0])):
                best = (prefix, src)
        return best[1] if best else self.source

    def _screen(self, ops: Iterable[Op]) -> tuple[list[Op], list[int]]:
        """The ops allowed through, and the positions of those dropped."""
        kept, dropped = [], []
        for i, op in enumerate(ops):
            if isinstance(op, PutOp) and op.value is not None:
                trial = self.court.trial(
                    text_of(op.value), self._source_for(op.namespace), "/".join(op.namespace)
                )
                self.trials.append((op.namespace, op.key, trial))
                if self.on_trial:
                    self.on_trial(op.namespace, op.key, trial)
                if not trial.approved:
                    if self.on_refused == "raise":
                        raise MemoryRefused(trial)
                    dropped.append(i)
                    continue
            kept.append(op)
        return kept, dropped

    @staticmethod
    def _merge(n: int, dropped: list[int], results: list[Result]) -> list[Result]:
        it = iter(results)
        return [None if i in dropped else next(it) for i in range(n)]

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        ops = list(ops)
        kept, dropped = self._screen(ops)
        return self._merge(len(ops), dropped, self.store.batch(kept) if kept else [])

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        ops = list(ops)
        kept, dropped = self._screen(ops)
        return self._merge(len(ops), dropped, await self.store.abatch(kept) if kept else [])
