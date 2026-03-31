from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState


class ProductOwnerAgent(BaseAgent):
    role = "product_owner"
    template_name = "product_owner.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        return f"Turn {turn}: You are the product_owner. Review the current sprint state and take action."
