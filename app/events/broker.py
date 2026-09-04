from __future__ import annotations

import asyncio
import json
from collections import deque
from collections.abc import AsyncIterator

from app.models import EventRecord


class EventBroker:
    def __init__(self, max_events: int = 200, queue_size: int = 100) -> None:
        self._events: deque[EventRecord] = deque(maxlen=max_events)
        self._subscribers: set[asyncio.Queue[EventRecord]] = set()
        self._queue_size = queue_size
        self._sequence = 0
        self._lock = asyncio.Lock()

    async def publish(self, **event: object) -> EventRecord:
        async with self._lock:
            self._sequence += 1
            record = EventRecord(sequence=self._sequence, **event)
            self._publish_locked(record)
            return record

    async def publish_record(self, record: EventRecord) -> EventRecord:
        async with self._lock:
            self._sequence = max(self._sequence, record.sequence)
            self._publish_locked(record)
            return record

    async def restore(self, events: list[EventRecord]) -> None:
        async with self._lock:
            combined = {event.sequence: event for event in (*self._events, *events)}
            self._events.clear()
            self._events.extend(combined[key] for key in sorted(combined))
            if combined:
                self._sequence = max(self._sequence, max(combined))

    async def clear(self) -> None:
        async with self._lock:
            self._events.clear()

    def _publish_locked(self, record: EventRecord) -> None:
        self._events.append(record)
        for queue in tuple(self._subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(record)

    async def stream(self, after: int = 0) -> AsyncIterator[str]:
        queue: asyncio.Queue[EventRecord] = asyncio.Queue(self._queue_size)
        async with self._lock:
            backlog = [event for event in self._events if event.sequence > after]
            self._subscribers.add(queue)

        try:
            for event in backlog:
                yield self._encode(event)

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield self._encode(event)
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    @staticmethod
    def _encode(event: EventRecord) -> str:
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        return f"id: {event.sequence}\nevent: {event.kind}\ndata: {payload}\n\n"
