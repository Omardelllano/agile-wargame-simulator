from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState


class ScrumMasterAgent(BaseAgent):
    role = "scrum_master"
    template_name = "scrum_master.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        return f"Turn {turn}: You are the scrum_master. Review the current sprint state and take action."
