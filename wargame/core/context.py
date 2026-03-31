from wargame.models.world_state import WorldState, SprintMetrics, StoryStatus


class ContextInjector:
    """Extracts per-agent context from WorldState for template rendering."""

    def inject(self, world_state: WorldState, agent_id: str) -> dict:
        """Return a dict of template variables for the given agent."""
        metrics = next(
            (m for m in world_state.sprint_history if m.sprint == world_state.current_sprint),
            SprintMetrics(sprint=world_state.current_sprint),
        )
        my_stories = [s for s in world_state.stories if s.assigned_to == agent_id]
        active_stories = [s for s in world_state.stories if s.status not in (StoryStatus.DONE,)][:12]

        return {
            "metrics": metrics,
            "my_stories": my_stories,
            "active_stories": active_stories,
        }
