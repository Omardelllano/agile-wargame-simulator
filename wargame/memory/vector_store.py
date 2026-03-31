import os
import uuid

from wargame.models.agent_response import AgentResponse


class AgentVectorStore:
    """Per-agent ChromaDB collections for RAG context retrieval."""

    def __init__(self, host: str | None = None, port: int = 8000):
        self._client = self._build_client(host, port)
        self._collections: dict = {}

    def _build_client(self, host: str | None, port: int):
        import chromadb

        resolved_host = host or os.environ.get("CHROMA_HOST", "")
        chroma_port = int(os.environ.get("CHROMA_PORT", str(port)))

        if resolved_host and resolved_host not in ("localhost", "127.0.0.1"):
            return chromadb.HttpClient(host=resolved_host, port=chroma_port)
        # Local / test: ephemeral in-memory (no Docker needed)
        return chromadb.EphemeralClient()

    def _collection(self, agent_id: str):
        if agent_id not in self._collections:
            self._collections[agent_id] = self._client.get_or_create_collection(
                name=f"agent_{agent_id}",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[agent_id]

    async def persist(self, agent_id: str, response: AgentResponse) -> None:
        col = self._collection(agent_id)
        document = (
            f"Sprint {response.sprint} Turn {response.turn}: "
            f"{response.action.value} — {response.rationale}"
        )
        meta = {
            "agent_id": agent_id,
            "sprint": response.sprint,
            "turn": response.turn,
            "action": response.action.value,
            "confidence": response.confidence,
        }
        col.add(
            documents=[document],
            metadatas=[meta],
            ids=[str(uuid.uuid4())],
        )

    async def query(self, agent_id: str, query: str, n_results: int = 5) -> list[dict]:
        col = self._collection(agent_id)
        count = col.count()
        if count == 0:
            return []
        results = col.query(
            query_texts=[query],
            n_results=min(n_results, count),
        )
        items = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            items.append({
                "summary": doc,
                "turn": meta.get("turn", 0),
                "sprint": meta.get("sprint", 0),
                "action": meta.get("action", ""),
            })
        return items
