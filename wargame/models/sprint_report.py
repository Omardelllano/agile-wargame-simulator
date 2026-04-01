from pydantic import BaseModel, Field
from datetime import datetime


class FrictionHotspot(BaseModel):
    agent_pair: tuple[str, str]
    conflict_count: int
    root_cause: str


class BlockedDependency(BaseModel):
    story_id: str
    blocked_by_agent: str
    blocking_reason: str
    days_blocked: int
    impact: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"


class PredictedRisk(BaseModel):
    id: str
    severity: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    sprint_impact: int
    description: str
    recommendation: str


class SprintReport(BaseModel):
    simulation_id: str
    sprint: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(ge=0.0, le=1.0)
    is_reliable: bool = True

    friction_index: float
    friction_hotspots: list[FrictionHotspot] = []
    blocked_dependencies: list[BlockedDependency] = []
    tech_debt_delta: int
    velocity: int
    velocity_decay_pct: float

    predicted_risks: list[PredictedRisk] = []
    recommendations: list[str] = []
    debt_capped: bool = False  # True when tech_debt_delta was clamped to 2× sprint velocity

    @classmethod
    def reliability_threshold(cls) -> float:
        return 0.70
