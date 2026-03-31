"""
tests/test_friction.py
FrictionDetector.score() contract:
  - returns 0.0 for empty event list
  - returns > 0 for any friction event
  - known conflict pairs (tech_lead / product_owner) score higher than unknown pairs
"""
import pytest

from wargame.core.friction import FrictionDetector
from wargame.models.events import AgentEvent, EventType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(event_type: EventType, source: str, target: str | None = None) -> AgentEvent:
    return AgentEvent(
        event_type=event_type,
        source_agent=source,
        target_agent=target,
        turn=1,
        sprint=1,
    )


@pytest.fixture
def detector():
    return FrictionDetector()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_empty_events_returns_zero(detector):
    assert detector.score([]) == 0.0


def test_single_conflict_event_is_positive(detector):
    events = [_event(EventType.CONFLICT, "tech_lead", "product_owner")]
    assert detector.score(events) > 0.0


def test_story_blocked_is_friction(detector):
    events = [_event(EventType.STORY_BLOCKED, "qa_engineer")]
    assert detector.score(events) > 0.0


def test_non_friction_event_contributes_zero_weight(detector):
    """A STORY_COMPLETED event carries no friction weight."""
    events = [_event(EventType.STORY_COMPLETED, "developer")]
    assert detector.score(events) == 0.0


def test_known_pair_scores_higher_than_unknown_pair(detector):
    """
    tech_lead vs product_owner is a known pair → CONFLICT counts double.
    unknown_a vs unknown_b is not a known pair → CONFLICT counts once.
    Both scenarios have the same total event count so the ratio differs.
    """
    known_events = [
        _event(EventType.CONFLICT, "tech_lead", "product_owner"),
        _event(EventType.STORY_COMPLETED, "developer"),  # neutral filler
    ]
    unknown_events = [
        _event(EventType.CONFLICT, "unknown_a", "unknown_b"),
        _event(EventType.STORY_COMPLETED, "developer"),  # neutral filler
    ]

    known_score   = detector.score(known_events)
    unknown_score = detector.score(unknown_events)

    assert known_score > unknown_score, (
        f"Expected known-pair score ({known_score}) > unknown-pair score ({unknown_score})"
    )


def test_all_known_pairs_are_detected(detector):
    """Every declared CONFLICT_PAIR should produce a higher score than an unknown pair."""
    unknown_baseline = detector.score([
        _event(EventType.CONFLICT, "x", "y"),
        _event(EventType.STORY_COMPLETED, "z"),
    ])

    for a, b in FrictionDetector.CONFLICT_PAIRS:
        score = detector.score([
            _event(EventType.CONFLICT, a, b),
            _event(EventType.STORY_COMPLETED, "developer"),
        ])
        assert score > unknown_baseline, f"Known pair {a}/{b} not scoring higher than unknown"


def test_score_capped_at_one(detector):
    """Score must never exceed 1.0 regardless of event volume."""
    events = [
        _event(EventType.CONFLICT, "tech_lead", "product_owner")
        for _ in range(100)
    ]
    assert detector.score(events) <= 1.0


def test_multiple_friction_types(detector):
    events = [
        _event(EventType.PR_VETOED,         "tech_lead"),
        _event(EventType.SECURITY_FLAG,     "security_architect"),
        _event(EventType.IMPEDIMENT_RAISED, "scrum_master"),
    ]
    assert detector.score(events) == 1.0  # 3 friction / 3 total = 1.0
