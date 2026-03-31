from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState


class SoftwareArchitectAgent(BaseAgent):
    role = "software_architect"
    template_name = "software_architect.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        return f"Turn {turn}: You are the software_architect. Review the current sprint state and take action."
