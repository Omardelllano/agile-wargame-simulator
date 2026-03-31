from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState


class TechLeadAgent(BaseAgent):
    role = "tech_lead"
    template_name = "tech_lead.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        return f"Turn {turn}: You are the tech_lead. Review the current sprint state and take action."
