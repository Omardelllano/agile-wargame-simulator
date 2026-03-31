import json
from pathlib import Path
from wargame.models.world_state import WorldState, Story, StoryStatus, SprintMetrics
from wargame.exceptions import ScenarioNotFoundError


def load_scenario(scenario_path: str) -> WorldState:
    """Load a scenario from a directory containing backlog.json."""
    path = Path(scenario_path)
    backlog_file = path / "backlog.json"
    if not backlog_file.exists():
        raise ScenarioNotFoundError(f"backlog.json not found in {scenario_path}")

    with open(backlog_file) as f:
        data = json.load(f)

    stories = []
    for epic in data.get("epics", []):
        for s in epic.get("stories", []):
            stories.append(Story(
                id=s["id"],
                epic_id=s["epic_id"],
                title=s["title"],
                points=s["points"],
                status=StoryStatus.TODO,
            ))

    import uuid
    return WorldState(
        simulation_id=str(uuid.uuid4()),
        scenario=data.get("scenario_id", "unknown"),
        total_sprints=data.get("total_sprints", 8),
        stories=stories,
    )
