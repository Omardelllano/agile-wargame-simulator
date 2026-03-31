from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState


class CloudEngineerAgent(BaseAgent):
    role = "cloud_engineer"
    template_name = "cloud_engineer.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        return f"Turn {turn}: You are the cloud_engineer. Review the current sprint state and take action."
