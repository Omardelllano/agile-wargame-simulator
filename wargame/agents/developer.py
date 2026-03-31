from wargame.agents.base import BaseAgent
from wargame.models.world_state import WorldState, StoryStatus


class DeveloperAgent(BaseAgent):
    role = "developer"
    template_name = "developer.j2"

    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str:
        in_progress = [
            s for s in world_state.stories
            if s.status == StoryStatus.IN_PROGRESS and s.assigned_to == self.role
        ]
        available = [
            s for s in world_state.stories
            if s.status == StoryStatus.TODO and s.blocked_by is None
        ][:3]

        lines = [f"Turn {turn}, Sprint {world_state.current_sprint}/{world_state.total_sprints}."]
        if in_progress:
            lines.append(
                "Your active stories: "
                + ", ".join(f"{s.id} ({s.points}pts, {s.status})" for s in in_progress)
            )
        elif available:
            lines.append(
                "Available stories to pick up: "
                + ", ".join(f"{s.id} ({s.points}pts)" for s in available)
            )
        else:
            lines.append("No stories currently assigned. Check for blockers or pick up backlog items.")

        lines.append(
            f"Tech debt total: {world_state.tech_debt_total}pts. "
            "Decide your action this turn."
        )
        return " ".join(lines)
