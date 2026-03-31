import asyncio
from collections.abc import Callable

from wargame.agents.base import BaseAgent
from wargame.core.events import EventBus
from wargame.models.agent_response import AgentResponse, ActionType
from wargame.models.events import AgentEvent, EventType
from wargame.models.world_state import WorldState


class TurnManager:
    """Runs all agents concurrently for one turn and publishes resulting events."""

    def __init__(self, agents: list[BaseAgent], event_bus: EventBus):
        self.agents = agents
        self.event_bus = event_bus

    async def run_turn(
        self,
        world_state: WorldState,
        turn_num: int,
        on_response: Callable[[AgentResponse], None] | None = None,
    ) -> list[AgentResponse]:
        responses: list[AgentResponse] = list(
            await asyncio.gather(*[agent.decide(world_state, turn_num) for agent in self.agents])
        )
        if on_response:
            for r in responses:
                on_response(r)
        events = self._responses_to_events(responses, world_state.current_sprint, turn_num)
        self.event_bus.publish_batch(events)
        return responses

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _responses_to_events(
        self,
        responses: list[AgentResponse],
        sprint: int,
        turn: int,
    ) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        for r in responses:
            if r.action == ActionType.BLOCK_DONE:
                for sid in r.referenced_stories:
                    events.append(AgentEvent(
                        event_type=EventType.STORY_BLOCKED,
                        source_agent=r.agent_id,
                        story_id=sid,
                        payload={"rationale": r.rationale},
                        turn=turn,
                        sprint=sprint,
                    ))
            elif r.action == ActionType.COMPLETE:
                for sid in r.referenced_stories:
                    events.append(AgentEvent(
                        event_type=EventType.STORY_COMPLETED,
                        source_agent=r.agent_id,
                        story_id=sid,
                        payload={},
                        turn=turn,
                        sprint=sprint,
                    ))
            elif r.action == ActionType.VETO:
                events.append(AgentEvent(
                    event_type=EventType.PR_VETOED,
                    source_agent=r.agent_id,
                    payload={"rationale": r.rationale},
                    turn=turn,
                    sprint=sprint,
                ))
            elif r.action == ActionType.FLAG:
                events.append(AgentEvent(
                    event_type=EventType.SECURITY_FLAG,
                    source_agent=r.agent_id,
                    payload={"rationale": r.rationale},
                    turn=turn,
                    sprint=sprint,
                ))
            elif r.action == ActionType.IMPEDIMENT:
                events.append(AgentEvent(
                    event_type=EventType.IMPEDIMENT_RAISED,
                    source_agent=r.agent_id,
                    payload={"rationale": r.rationale},
                    turn=turn,
                    sprint=sprint,
                ))
            elif r.action == ActionType.REPRIORITIZE:
                events.append(AgentEvent(
                    event_type=EventType.SCOPE_CHANGED,
                    source_agent=r.agent_id,
                    payload={"rationale": r.rationale},
                    turn=turn,
                    sprint=sprint,
                ))
            if r.tech_debt_added > 0:
                events.append(AgentEvent(
                    event_type=EventType.TECH_DEBT_ADDED,
                    source_agent=r.agent_id,
                    payload={"points": r.tech_debt_added},
                    turn=turn,
                    sprint=sprint,
                ))
        return events
