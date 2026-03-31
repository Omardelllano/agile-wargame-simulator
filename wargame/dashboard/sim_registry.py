"""
In-process simulation registry.
Maps sim_id -> SimState (queue + reports + status).
"""
import asyncio
from dataclasses import dataclass, field

_registry: dict[str, "SimState"] = {}

_SENTINEL = object()  # signals SSE generator to stop


@dataclass
class SimState:
    sim_id: str
    provider: str
    scenario: str
    total_sprints: int
    status: str = "pending"        # pending | running | done | error
    current_sprint: int = 0
    reports: list[dict] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    # The Orchestrator generates its own UUID stored in the DB; we map it here
    db_sim_id: str | None = None


def create_sim(sim_id: str, provider: str, scenario: str, total_sprints: int) -> SimState:
    state = SimState(
        sim_id=sim_id,
        provider=provider,
        scenario=scenario,
        total_sprints=total_sprints,
    )
    _registry[sim_id] = state
    return state


def get_sim(sim_id: str) -> SimState | None:
    return _registry.get(sim_id)


def list_sims() -> list[SimState]:
    return list(_registry.values())


def push_event(state: SimState, event_type: str, data: dict) -> None:
    """Non-blocking push — safe to call from sync callbacks."""
    state.queue.put_nowait({"event": event_type, "data": data})


def push_done(state: SimState) -> None:
    """Push sentinel to signal SSE stream end."""
    state.queue.put_nowait(_SENTINEL)


def is_sentinel(item: object) -> bool:
    return item is _SENTINEL
