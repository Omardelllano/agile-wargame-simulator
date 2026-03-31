import os
from collections.abc import Callable
from pathlib import Path

from wargame.core.events import EventBus
from wargame.core.friction import FrictionDetector
from wargame.core.state import load_scenario
from wargame.core.turn import TurnManager
from wargame.god_agent.exporter import ReportExporter
from wargame.god_agent.god_agent import GodAgent
from wargame.memory.interaction_log import InteractionLog
from wargame.memory.vector_store import AgentVectorStore
from wargame.models.agent_response import AgentResponse
from wargame.models.sprint_report import SprintReport
from wargame.models.world_state import SprintMetrics, WorldState
from wargame.prompts.renderer import PromptRenderer
from wargame.providers.base import BaseLLMProvider


class Orchestrator:
    def __init__(
        self,
        provider: BaseLLMProvider,
        scenario_path: str,
        total_sprints: int = 8,
        db_url: str = "sqlite:///./output/wargame.db",
        output_dir: str = "output",
        turns_per_sprint: int | None = None,
    ):
        self.provider = provider
        self.scenario_path = scenario_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.turns_per_sprint = turns_per_sprint or int(
            os.environ.get("DEFAULT_TURNS_PER_SPRINT", "5")
        )

        self.state: WorldState = load_scenario(scenario_path)
        self.state.total_sprints = total_sprints

        self.event_bus = EventBus()
        self.interaction_log = InteractionLog(db_url)
        self.vector_store = AgentVectorStore()
        self.renderer = PromptRenderer()
        self.exporter = ReportExporter(str(self.output_dir))
        self.god_agent = GodAgent(provider=provider, interaction_log=self.interaction_log)

        self.friction_detector = FrictionDetector()
        self._agents = self._build_agents()
        self.turn_manager = TurnManager(self._agents, self.event_bus)

    def _build_agents(self):
        from wargame.agents.cloud_engineer import CloudEngineerAgent
        from wargame.agents.developer import DeveloperAgent
        from wargame.agents.product_owner import ProductOwnerAgent
        from wargame.agents.qa_engineer import QAEngineerAgent
        from wargame.agents.scrum_master import ScrumMasterAgent
        from wargame.agents.security_architect import SecurityArchitectAgent
        from wargame.agents.software_architect import SoftwareArchitectAgent
        from wargame.agents.tech_lead import TechLeadAgent

        return [
            cls(self.provider, self.vector_store, self.renderer)
            for cls in [
                DeveloperAgent, QAEngineerAgent, TechLeadAgent, ProductOwnerAgent,
                SecurityArchitectAgent, CloudEngineerAgent, ScrumMasterAgent, SoftwareArchitectAgent,
            ]
        ]

    async def run(
        self,
        on_turn_complete: Callable[[int, int, list[AgentResponse]], None] | None = None,
        on_sprint_complete: Callable[[SprintReport], None] | None = None,
    ) -> list[SprintReport]:
        """Main simulation loop. Returns one SprintReport per sprint."""
        reports: list[SprintReport] = []
        for sprint_num in range(1, self.state.total_sprints + 1):
            report = await self._run_sprint(sprint_num, on_turn_complete, on_sprint_complete)
            reports.append(report)
        return reports

    async def _run_sprint(
        self,
        sprint_num: int,
        on_turn_complete: Callable[[int, int, list[AgentResponse]], None] | None,
        on_sprint_complete: Callable[[SprintReport], None] | None = None,
    ) -> SprintReport:
        self.state.current_sprint = sprint_num
        self.state.sprint_history.append(SprintMetrics(sprint=sprint_num))
        self.event_bus.clear()

        for turn_num in range(1, self.turns_per_sprint + 1):
            self.state.current_turn = turn_num
            responses = await self._run_turn(turn_num)
            if on_turn_complete:
                on_turn_complete(sprint_num, turn_num, responses)

        report = await self.god_agent.synthesize(self.state)
        self.interaction_log.record_sprint_report(report)
        # Note: exporter.export() is called inside GodAgent.synthesize() when is_reliable=True
        if on_sprint_complete:
            on_sprint_complete(report)
        return report

    async def _run_turn(self, turn_num: int) -> list[AgentResponse]:
        responses = await self.turn_manager.run_turn(self.state, turn_num)
        events = self.event_bus.drain()

        # Accumulate tech debt
        for r in responses:
            self.state.tech_debt_total += r.tech_debt_added

        # Update current sprint metrics
        current_metrics = self.state.sprint_history[-1]
        blocked = sum(1 for e in events if e.event_type.value == "STORY_BLOCKED")
        current_metrics.blocked_count += blocked
        # Accumulate friction index (running average over turns)
        fi = self.friction_detector.score(events)
        turns_so_far = self.state.current_turn
        current_metrics.friction_index = (
            (current_metrics.friction_index * (turns_so_far - 1) + fi) / turns_so_far
        )

        self.interaction_log.record_turn(
            simulation_id=self.state.simulation_id,
            sprint=self.state.current_sprint,
            turn=turn_num,
            responses=responses,
            events=events,
        )
        self.interaction_log.record_snapshot(
            simulation_id=self.state.simulation_id,
            sprint=self.state.current_sprint,
            turn=turn_num,
            snapshot=self.state.snapshot(),
        )
        return responses
