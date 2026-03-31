from abc import ABC, abstractmethod

from wargame.exceptions import GroundingError
from wargame.memory.vector_store import AgentVectorStore
from wargame.models.agent_response import AgentResponse
from wargame.models.world_state import WorldState, SprintMetrics, StoryStatus
from wargame.prompts.renderer import PromptRenderer
from wargame.providers.base import BaseLLMProvider


class BaseAgent(ABC):
    role: str = "base"
    template_name: str = ""

    def __init__(
        self,
        provider: BaseLLMProvider,
        vector_store: AgentVectorStore,
        renderer: PromptRenderer,
    ):
        self.provider = provider
        self.vector_store = vector_store
        self.renderer = renderer

    async def decide(self, world_state: WorldState, turn: int) -> AgentResponse:
        """Build prompt → call LLM → validate grounding → persist to vector store → return."""
        context = await self._retrieve_context(world_state)
        system_prompt = self.renderer.render(
            self.template_name,
            role=self.role,
            world_state=world_state,
            context=context,
            **self._template_extras(world_state),
        )
        user_prompt = self._build_user_prompt(world_state, turn)
        response = await self.provider.complete(system_prompt, user_prompt)
        # Stamp correct agent_id / turn / sprint regardless of what mock returns
        response = response.model_copy(update={
            "agent_id": self.role,
            "turn": turn,
            "sprint": world_state.current_sprint,
        })
        self._validate_grounding(response, world_state)
        await self.vector_store.persist(self.role, response)
        return response

    def _validate_grounding(self, response: AgentResponse, state: WorldState) -> None:
        """Raise GroundingError if response references a story ID not in the backlog."""
        real_ids = {s.id for s in state.stories}
        for story_id in response.referenced_stories:
            if story_id not in real_ids:
                raise GroundingError(
                    f"[{self.role}] hallucinated story ID: {story_id}"
                )

    def _template_extras(self, world_state: WorldState) -> dict:
        """Inject sprint metrics and active stories for template rendering."""
        metrics = next(
            (m for m in world_state.sprint_history if m.sprint == world_state.current_sprint),
            SprintMetrics(sprint=world_state.current_sprint),
        )
        active_stories = [
            s for s in world_state.stories
            if s.status not in (StoryStatus.DONE,)
        ][:12]
        return {"metrics": metrics, "active_stories": active_stories}

    @abstractmethod
    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str: ...

    async def _retrieve_context(self, world_state: WorldState) -> list[dict]:
        """RAG: fetch last 5 relevant interactions for this agent from ChromaDB."""
        return await self.vector_store.query(
            agent_id=self.role,
            query=f"sprint {world_state.current_sprint} decisions",
            n_results=5,
        )
