from enum import Enum
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    APPROVE      = "APPROVE"
    VETO         = "VETO"
    BLOCK_DONE   = "BLOCK_DONE"
    COMPLETE     = "COMPLETE"
    ESCALATE     = "ESCALATE"
    FLAG         = "FLAG"
    REPRIORITIZE = "REPRIORITIZE"
    IMPEDIMENT   = "IMPEDIMENT"
    IDLE         = "IDLE"


class AgentResponse(BaseModel):
    agent_id: str
    turn: int
    sprint: int
    action: ActionType
    rationale: str = Field(max_length=500)
    referenced_stories: list[str] = []
    events: list[dict] = []
    artifacts: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    tech_debt_added: int = 0
