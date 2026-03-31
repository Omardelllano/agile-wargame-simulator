import asyncio

from wargame.god_agent import mapper
from wargame.god_agent.exporter import ReportExporter
from wargame.god_agent.reducer import GodAgentReducer
from wargame.memory.interaction_log import InteractionLog
from wargame.models.sprint_report import SprintReport
from wargame.models.world_state import WorldState
from wargame.providers.base import BaseLLMProvider


class GodAgent:
    """
    Read-only observer. Never modifies WorldState.
    Runs after every sprint. Produces a SprintReport via MAP → REDUCE → EXPORT.
    """

    def __init__(self, provider: BaseLLMProvider, interaction_log: InteractionLog):
        self.provider = provider
        self.log = interaction_log
        self.reducer = GodAgentReducer(provider)
        self.exporter = ReportExporter()

    async def synthesize(self, world_state: WorldState) -> SprintReport:
        """
        1. Run all 4 MAP functions in parallel (asyncio.gather)
        2. REDUCE → SprintReport
        3. EXPORT if confidence >= 0.70
        4. Return report regardless
        """
        sprint = world_state.current_sprint

        # --- MAP phase (parallel, no LLM) ---
        map_results = await asyncio.gather(
            mapper.map_friction(self.log, sprint),
            mapper.map_dependencies(self.log, sprint),
            mapper.map_tech_debt(self.log, sprint),
            mapper.map_velocity(self.log, sprint),
        )

        # --- REDUCE phase ---
        report = await self.reducer.reduce(map_results, world_state)

        # --- EXPORT phase (only if reliable) ---
        if report.is_reliable:
            self.exporter.export(report)

        return report
