"""
GET /graph/{sim_id}
Returns agent interaction matrix for the D3 force graph.
Derives data from interaction_turns (action-based friction) because
the mock provider generates no CONFLICT events with explicit target_agents.
"""
import os
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from wargame.memory.interaction_log import InteractionTurn

router = APIRouter()

# ---------------------------------------------------------------------------
# Friction weight per action type (used to compute per-node and per-link friction)
# ---------------------------------------------------------------------------
_FRICTION_WEIGHTS: dict[str, float] = {
    "VETO":         1.0,
    "BLOCK_DONE":   0.9,
    "FLAG":         0.8,
    "IMPEDIMENT":   0.7,
    "ESCALATE":     0.5,
    "REPRIORITIZE": 0.4,
}

# Known high-friction pairs receive a 2× multiplier so they register >= 0.60
_KNOWN_PAIRS: set[frozenset] = {
    frozenset({"tech_lead", "product_owner"}),
    frozenset({"qa_engineer", "developer"}),
    frozenset({"security_architect", "cloud_engineer"}),
    frozenset({"software_architect", "developer"}),
}
_KNOWN_PAIR_MULTIPLIER = 2.0

# Minimum shared story references to show an edge for non-known pairs
_MIN_SHARED_STORIES = 2


@router.get("/graph/{sim_id}")
async def get_graph(sim_id: str):
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./output/wargame.db")
    engine = create_engine(db_url)

    with Session(engine) as session:
        turns = (
            session.query(InteractionTurn)
            .filter(InteractionTurn.simulation_id == sim_id)
            .order_by(InteractionTurn.id)
            .all()
        )

    if not turns:
        raise HTTPException(status_code=404, detail="No interaction data for this simulation")

    # ------------------------------------------------------------------
    # Per-agent aggregation
    # ------------------------------------------------------------------
    agent_actions:   dict[str, int]   = defaultdict(int)
    agent_fw:        dict[str, float] = defaultdict(float)   # friction weight sum
    agent_last:      dict[str, str]   = {}
    agent_stories:   dict[str, set]   = defaultdict(set)

    for row in turns:
        a = row.agent_id
        agent_actions[a] += 1
        agent_last[a] = row.action
        agent_fw[a] += _FRICTION_WEIGHTS.get(row.action, 0.0)
        for sid in (row.referenced_stories or []):
            agent_stories[a].add(sid)

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------
    nodes = []
    for agent_id, total in agent_actions.items():
        node_friction = agent_fw[agent_id] / total if total else 0.0
        nodes.append({
            "id":          agent_id,
            "actions":     total,
            "last_action": agent_last.get(agent_id, "IDLE"),
            "friction":    round(node_friction, 3),
        })

    # ------------------------------------------------------------------
    # Links — one per unordered pair
    # ------------------------------------------------------------------
    agent_ids = sorted(agent_actions.keys())
    links = []

    for i, a in enumerate(agent_ids):
        for b in agent_ids[i + 1:]:
            pair = frozenset({a, b})
            known = pair in _KNOWN_PAIRS

            # Shared story references → edge thickness proxy
            shared = agent_stories[a] & agent_stories[b]
            interactions = len(shared) + 1   # +1 baseline so all pairs have ≥ 1

            # Skip sparse edges that aren't known pairs
            if not known and len(shared) < _MIN_SHARED_STORIES:
                continue

            # Friction for this link
            total_actions = agent_actions[a] + agent_actions[b]
            raw = (agent_fw[a] + agent_fw[b]) / total_actions if total_actions else 0.0
            link_friction = min(raw * _KNOWN_PAIR_MULTIPLIER, 1.0) if known else raw

            links.append({
                "source":       a,
                "target":       b,
                "interactions": interactions,
                "friction":     round(link_friction, 3),
            })

    return {"nodes": nodes, "links": links}
