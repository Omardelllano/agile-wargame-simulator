from enum import Enum
from pydantic import BaseModel


class EventType(str, Enum):
    STORY_BLOCKED     = "STORY_BLOCKED"
    STORY_UNBLOCKED   = "STORY_UNBLOCKED"
    STORY_COMPLETED   = "STORY_COMPLETED"
    PR_VETOED         = "PR_VETOED"
    SCOPE_CHANGED     = "SCOPE_CHANGED"
    IMPEDIMENT_RAISED = "IMPEDIMENT_RAISED"
    SECURITY_FLAG     = "SECURITY_FLAG"
    TECH_DEBT_ADDED   = "TECH_DEBT_ADDED"
    CONFLICT          = "CONFLICT"


class AgentEvent(BaseModel):
    event_type: EventType
    source_agent: str
    target_agent: str | None = None
    story_id: str | None = None
    payload: dict = {}
    turn: int
    sprint: int
