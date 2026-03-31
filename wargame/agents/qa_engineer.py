from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState


class QAEngineerAgent(BaseAgent):
    role = "qa_engineer"
    template_name = "qa_engineer.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        return f"Turn {turn}: You are the qa_engineer. Review the current sprint state and take action."
