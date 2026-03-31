from wargame.models.events import AgentEvent, EventType

# Event types that represent friction / conflict
_FRICTION_TYPES = {
    EventType.STORY_BLOCKED,
    EventType.PR_VETOED,
    EventType.SECURITY_FLAG,
    EventType.IMPEDIMENT_RAISED,
    EventType.CONFLICT,
}

# Friction pairs: CONFLICT events between these agents count double
_PAIR_SET: set[frozenset] = {
    frozenset({"tech_lead", "product_owner"}),
    frozenset({"qa_engineer", "developer"}),
    frozenset({"security_architect", "cloud_engineer"}),
    frozenset({"software_architect", "developer"}),
}


class FrictionDetector:
    CONFLICT_PAIRS = [
        ("tech_lead", "product_owner"),
        ("qa_engineer", "developer"),
        ("security_architect", "cloud_engineer"),
        ("software_architect", "developer"),
    ]

    def score(self, events: list[AgentEvent]) -> float:
        """
        Returns Friction Index for a turn: 0.0 (no friction) to 1.0 (max).
        Formula: weighted_conflict_events / total_events, capped at 1.0.
        A CONFLICT event between a known friction pair counts double.
        """
        total = len(events)
        if total == 0:
            return 0.0

        conflict_weight = 0.0
        for e in events:
            if e.event_type not in _FRICTION_TYPES:
                continue
            weight = 1.0
            if e.event_type == EventType.CONFLICT and e.target_agent is not None:
                pair = frozenset({e.source_agent, e.target_agent})
                if pair in _PAIR_SET:
                    weight = 2.0
            conflict_weight += weight

        return min(conflict_weight / total, 1.0)
