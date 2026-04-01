"""
MAP phase of the God Agent pipeline.
All 4 functions query SQLite via SQLAlchemy — zero LLM calls.
Each returns a plain dict consumed by GodAgentReducer.
"""
from collections import defaultdict

from sqlalchemy.orm import Session

from wargame.memory.interaction_log import (
    AgentEventRow,
    InteractionLog,
    InteractionTurn,
    WorldStateSnapshot,
)

# Friction-generating event types
_FRICTION_EVENTS = {
    "STORY_BLOCKED",
    "PR_VETOED",
    "SECURITY_FLAG",
    "IMPEDIMENT_RAISED",
    "CONFLICT",
}

# Known friction pairs (source → target)
_FRICTION_PAIRS: set[frozenset] = {
    frozenset({"tech_lead", "product_owner"}),
    frozenset({"qa_engineer", "developer"}),
    frozenset({"security_architect", "cloud_engineer"}),
    frozenset({"software_architect", "developer"}),
}

# Role → conflict partner mapping for root-cause narration
_PAIR_CAUSES: dict[frozenset, str] = {
    frozenset({"tech_lead", "product_owner"}):
        "Tech Lead perfectionism vs. Product Owner scope pressure",
    frozenset({"qa_engineer", "developer"}):
        "QA pessimism bias blocking Developer throughput",
    frozenset({"security_architect", "cloud_engineer"}):
        "Security requirements complicating IaC automation",
    frozenset({"software_architect", "developer"}):
        "Architecture vision slowing Developer delivery speed",
}

# Story-point default when a story is not found in snapshot (shouldn't happen)
_DEFAULT_POINTS = 5

# Phrases in blocking_reason that indicate a preemptive (invalid) block
_PREEMPTIVE_PHRASES = [
    "preemptively",
    "no stories have been completed yet",
    "not yet",
    "must preemptively",
    "future done status",
]


async def map_friction(log: InteractionLog, sprint: int) -> dict:
    """
    Returns friction hotspots for the sprint.
    Hotspot = any (source_agent) that emitted friction events, grouped by known pairs.
    """
    with Session(log.engine) as session:
        rows = (
            session.query(AgentEventRow)
            .filter(
                AgentEventRow.sprint == sprint,
                AgentEventRow.event_type.in_(_FRICTION_EVENTS),
            )
            .all()
        )

    if not rows:
        return {"sprint": sprint, "friction_hotspots": [], "total_friction_events": 0}

    # Count friction events per agent
    by_agent: dict[str, int] = defaultdict(int)
    for row in rows:
        by_agent[row.source_agent] += 1

    # Build hotspots for known conflict pairs
    hotspots: list[dict] = []
    seen_pairs: set[frozenset] = set()

    for row in rows:
        source = row.source_agent
        for pair in _FRICTION_PAIRS:
            if source in pair and pair not in seen_pairs:
                other = next(a for a in pair if a != source)
                other_count = by_agent.get(other, 0)
                if other_count > 0 or by_agent[source] > 0:
                    seen_pairs.add(pair)
                    hotspots.append({
                        "agent_pair": sorted(pair),
                        "conflict_count": by_agent[source] + other_count,
                        "root_cause": _PAIR_CAUSES.get(pair, f"{source} vs {other} friction"),
                    })

    # Add singleton hotspots for high-friction agents not in known pairs
    # NOTE: agent_pair must always be two distinct agents — skip self-pairs
    for agent, count in by_agent.items():
        if count >= 2:
            in_known = any(agent in p for p in seen_pairs)
            if not in_known:
                # Self-conflict entries are a data artefact (e.g. IMPEDIMENT_RAISED
                # by scrum_master has no target_agent), so we skip them entirely.
                pass

    return {
        "sprint": sprint,
        "friction_hotspots": hotspots,
        "total_friction_events": len(rows),
        "friction_index": min(len(rows) / max(len(rows) * 2, 1), 1.0),
    }


async def map_dependencies(log: InteractionLog, sprint: int) -> dict:
    """
    Returns blocked dependencies: stories with STORY_BLOCKED events this sprint.
    """
    with Session(log.engine) as session:
        blocked_rows = (
            session.query(AgentEventRow)
            .filter(
                AgentEventRow.sprint == sprint,
                AgentEventRow.event_type == "STORY_BLOCKED",
            )
            .all()
        )
        unblocked_ids = {
            row.story_id
            for row in session.query(AgentEventRow)
            .filter(
                AgentEventRow.sprint == sprint,
                AgentEventRow.event_type == "STORY_UNBLOCKED",
            )
            .all()
            if row.story_id
        }

    seen: set[str] = set()
    deps: list[dict] = []
    for row in blocked_rows:
        sid = row.story_id or "UNKNOWN"
        if sid in seen or sid in unblocked_ids:
            continue
        seen.add(sid)
        payload = row.payload or {}
        rationale = payload.get("rationale", "No reason recorded")
        # Rough impact from story points — not available here, use heuristic
        deps.append({
            "story_id": sid,
            "blocked_by_agent": row.source_agent,
            "blocking_reason": rationale[:200],
            "days_blocked": row.turn,          # proxy: turn number when blocked
            "impact": _infer_impact(row.source_agent),
        })

    # Filter out preemptive blocks (QA/others blocking TODO stories with
    # rationale language that indicates no real evidence of failure yet)
    filtered: list[dict] = []
    for dep in deps:
        reason = dep.get("blocking_reason", "").lower()
        is_preemptive = any(phrase in reason for phrase in _PREEMPTIVE_PHRASES)
        if not is_preemptive:
            filtered.append(dep)

    # Sort by days_blocked descending, cap at 5 to keep report concise
    filtered.sort(key=lambda x: x.get("days_blocked", 0), reverse=True)
    filtered = filtered[:5]

    return {
        "sprint": sprint,
        "blocked_dependencies": filtered,
        "total_blocked": len(filtered),
    }


async def map_tech_debt(log: InteractionLog, sprint: int) -> dict:
    """
    Returns total tech_debt_added across all agents this sprint.
    Also returns the raw total so the reducer can apply a per-sprint cap
    once velocity (completed story points) is known.
    """
    with Session(log.engine) as session:
        rows = (
            session.query(InteractionTurn)
            .filter(InteractionTurn.sprint == sprint)
            .all()
        )

    debt_by_agent: dict[str, int] = defaultdict(int)
    total = 0
    for row in rows:
        debt = row.tech_debt_added or 0
        if debt > 0:
            debt_by_agent[row.agent_id] += debt
            total += debt

    return {
        "sprint": sprint,
        "tech_debt_delta": total,
        "debt_by_agent": dict(debt_by_agent),
    }


async def map_velocity(log: InteractionLog, sprint: int) -> dict:
    """
    Returns velocity (story points completed) and decay vs. previous sprint.
    Uses STORY_COMPLETED events + world_state_snapshot for point values.
    """
    with Session(log.engine) as session:
        completed_events = (
            session.query(AgentEventRow)
            .filter(
                AgentEventRow.sprint == sprint,
                AgentEventRow.event_type == "STORY_COMPLETED",
            )
            .all()
        )
        completed_story_ids = {e.story_id for e in completed_events if e.story_id}

        # Last snapshot for this sprint (most up-to-date story state)
        last_snap = (
            session.query(WorldStateSnapshot)
            .filter(WorldStateSnapshot.sprint == sprint)
            .order_by(WorldStateSnapshot.turn.desc())
            .first()
        )

        # Previous sprint's last snapshot (for decay calculation)
        prev_snap = (
            session.query(WorldStateSnapshot)
            .filter(WorldStateSnapshot.sprint == sprint - 1)
            .order_by(WorldStateSnapshot.turn.desc())
            .first()
        ) if sprint > 1 else None

    # Resolve story points from snapshot
    velocity = 0
    if last_snap and completed_story_ids:
        snap_data = last_snap.snapshot_json
        points_by_id = {s["id"]: s["points"] for s in snap_data.get("stories", [])}
        velocity = sum(points_by_id.get(sid, _DEFAULT_POINTS) for sid in completed_story_ids)

    # Previous sprint velocity from sprint_history in snapshot
    prev_velocity = 0
    if prev_snap:
        prev_data = prev_snap.snapshot_json
        for m in prev_data.get("sprint_history", []):
            if m["sprint"] == sprint - 1:
                prev_velocity = m.get("velocity", 0)
                break

    if prev_velocity > 0:
        decay_pct = round((prev_velocity - velocity) / prev_velocity * 100, 1)
    else:
        decay_pct = 0.0

    return {
        "sprint": sprint,
        "velocity": velocity,
        "velocity_decay_pct": decay_pct,
        "completed_story_ids": list(completed_story_ids),
        "total_completed": len(completed_story_ids),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_impact(agent: str) -> str:
    """Heuristic impact from the blocking agent's role."""
    high_impact = {"security_architect", "tech_lead", "software_architect"}
    medium_impact = {"qa_engineer", "cloud_engineer"}
    if agent in high_impact:
        return "HIGH"
    if agent in medium_impact:
        return "MEDIUM"
    return "LOW"
