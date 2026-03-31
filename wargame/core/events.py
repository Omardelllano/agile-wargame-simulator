from wargame.models.events import AgentEvent


class EventBus:
    def __init__(self):
        self._events: list[AgentEvent] = []

    def publish(self, event: AgentEvent) -> None:
        self._events.append(event)

    def publish_batch(self, events: list[AgentEvent]) -> None:
        self._events.extend(events)

    def get_events(self) -> list[AgentEvent]:
        return list(self._events)

    def drain(self) -> list[AgentEvent]:
        """Return all events and clear the buffer atomically."""
        events = list(self._events)
        self._events.clear()
        return events

    def clear(self) -> None:
        self._events.clear()
