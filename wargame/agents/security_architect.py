from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState


class SecurityArchitectAgent(BaseAgent):
    role = "security_architect"
    template_name = "security_architect.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        return f"Turn {turn}: You are the security_architect. Review the current sprint state and take action."
