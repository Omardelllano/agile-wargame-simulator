from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class StoryStatus(str, Enum):
    TODO        = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW   = "IN_REVIEW"
    BLOCKED     = "BLOCKED"
    DONE        = "DONE"


class Story(BaseModel):
    id: str
    epic_id: str
    title: str
    points: int
    status: StoryStatus = StoryStatus.TODO
    assigned_to: str | None = None
    blocked_by: str | None = None
    blocked_days: int = 0


class SprintMetrics(BaseModel):
    sprint: int
    velocity: int = 0
    friction_index: float = 0.0
    tech_debt_delta: int = 0
    blocked_count: int = 0


class WorldState(BaseModel):
    simulation_id: str
    scenario: str
    current_sprint: int = 1
    current_turn: int = 0
    total_sprints: int = 8
    stories: list[Story] = []
    sprint_history: list[SprintMetrics] = []
    tech_debt_total: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def snapshot(self) -> dict:
        return self.model_dump(mode="json")
