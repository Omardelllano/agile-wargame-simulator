import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Session
from wargame.models.agent_response import AgentResponse
from wargame.models.events import AgentEvent
from wargame.models.sprint_report import SprintReport


class Base(DeclarativeBase):
    pass


class InteractionTurn(Base):
    __tablename__ = "interaction_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String, nullable=False)
    sprint = Column(Integer, nullable=False)
    turn = Column(Integer, nullable=False)
    agent_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    referenced_stories = Column(JSON, default=list)
    events = Column(JSON, default=list)
    artifacts = Column(JSON, default=list)
    confidence = Column(Float, default=1.0)
    tech_debt_added = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentEventRow(Base):
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String, nullable=False)
    sprint = Column(Integer, nullable=False)
    turn = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    source_agent = Column(String, nullable=False)
    target_agent = Column(String, nullable=True)
    story_id = Column(String, nullable=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class SprintReportRow(Base):
    __tablename__ = "sprint_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String, nullable=False)
    sprint = Column(Integer, nullable=False)
    report_json = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=False)
    is_reliable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorldStateSnapshot(Base):
    __tablename__ = "world_state_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(String, nullable=False)
    sprint = Column(Integer, nullable=False)
    turn = Column(Integer, nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class InteractionLog:
    def __init__(self, database_url: str = "sqlite:///./output/wargame.db"):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)

    def record_turn(
        self,
        simulation_id: str,
        sprint: int,
        turn: int,
        responses: list[AgentResponse],
        events: list[AgentEvent],
    ) -> None:
        with Session(self.engine) as session:
            for r in responses:
                row = InteractionTurn(
                    simulation_id=simulation_id,
                    sprint=sprint,
                    turn=turn,
                    agent_id=r.agent_id,
                    action=r.action.value,
                    rationale=r.rationale,
                    referenced_stories=r.referenced_stories,
                    events=r.events,
                    artifacts=r.artifacts,
                    confidence=r.confidence,
                    tech_debt_added=r.tech_debt_added,
                )
                session.add(row)
            for e in events:
                row = AgentEventRow(
                    simulation_id=simulation_id,
                    sprint=sprint,
                    turn=turn,
                    event_type=e.event_type.value,
                    source_agent=e.source_agent,
                    target_agent=e.target_agent,
                    story_id=e.story_id,
                    payload=e.payload,
                )
                session.add(row)
            session.commit()

    def record_sprint_report(self, report: SprintReport) -> None:
        with Session(self.engine) as session:
            row = SprintReportRow(
                simulation_id=report.simulation_id,
                sprint=report.sprint,
                report_json=json.loads(report.model_dump_json()),
                confidence_score=report.confidence_score,
                is_reliable=report.is_reliable,
            )
            session.add(row)
            session.commit()

    def record_snapshot(self, simulation_id: str, sprint: int, turn: int, snapshot: dict) -> None:
        with Session(self.engine) as session:
            row = WorldStateSnapshot(
                simulation_id=simulation_id,
                sprint=sprint,
                turn=turn,
                snapshot_json=snapshot,
            )
            session.add(row)
            session.commit()
