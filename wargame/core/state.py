import json
from pathlib import Path
from wargame.models.world_state import WorldState, Story, StoryStatus, SprintMetrics
from wargame.models.agent_response import AgentResponse, ActionType
from wargame.exceptions import ScenarioNotFoundError


def apply_agent_action(state: WorldState, response: AgentResponse) -> set[str]:
    """
    Mutate story statuses based on a single agent response.
    Returns the set of story IDs that moved to DONE this call.

    State machine:
      TODO        --(APPROVE)-->  IN_PROGRESS
      IN_PROGRESS --(COMPLETE)--> DONE
      IN_PROGRESS --(BLOCK_DONE)--> BLOCKED
      IN_PROGRESS | BLOCKED --(VETO)--> TODO
    """
    if not response.referenced_stories:
        return set()

    story_map = {s.id: s for s in state.stories}
    current_metrics = next(
        (m for m in state.sprint_history if m.sprint == state.current_sprint),
        None,
    )
    newly_done: set[str] = set()

    if response.action == ActionType.APPROVE:
        for sid in response.referenced_stories:
            story = story_map.get(sid)
            if story and story.status == StoryStatus.TODO:
                story.status = StoryStatus.IN_PROGRESS
                story.assigned_to = response.agent_id

    elif response.action == ActionType.COMPLETE:
        for sid in response.referenced_stories:
            story = story_map.get(sid)
            if story and story.status == StoryStatus.IN_PROGRESS:
                story.status = StoryStatus.DONE
                story.assigned_to = None
                newly_done.add(sid)
                if current_metrics is not None:
                    current_metrics.velocity += story.points

    elif response.action == ActionType.BLOCK_DONE:
        for sid in response.referenced_stories:
            story = story_map.get(sid)
            if story and story.status == StoryStatus.IN_PROGRESS:
                story.status = StoryStatus.BLOCKED
                story.blocked_by = response.agent_id

    elif response.action == ActionType.VETO:
        for sid in response.referenced_stories:
            story = story_map.get(sid)
            if story and story.status in (StoryStatus.IN_PROGRESS, StoryStatus.BLOCKED):
                story.status = StoryStatus.TODO
                story.assigned_to = None
                story.blocked_by = None

    return newly_done


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
