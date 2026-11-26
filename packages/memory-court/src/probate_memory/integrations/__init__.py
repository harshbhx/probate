"""Put the memory court in front of memory systems people already use.

- `probate_memory.integrations.mem0.CourtedMemory`: wraps a Mem0 `Memory` or `MemoryClient`
- `probate_memory.integrations.langgraph.CourtedStore`: wraps any LangGraph `BaseStore`
- `probate_memory.integrations.letta.CourtedArchive`: guards a Letta agent's archival memory

Each one puts the memory on trial first and only writes it if the court approves it. A convicted
or contested memory is never written; by default it is dropped and reported, or raised as
`MemoryRefused` with `on_refused="raise"`.
"""
