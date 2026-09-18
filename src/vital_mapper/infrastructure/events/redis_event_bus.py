from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis

from vital_mapper.application.ports.event_bus_port import EventBusPort
from vital_mapper.domain.events import DomainEvent

STREAM_KEY = "vital_mapper:events"


class RedisEventBus(EventBusPort):
    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url, decode_responses=True)

    async def publish(self, event: DomainEvent) -> None:
        # Die eigentliche Quelle der Wahrheit ist die Outbox-Tabelle (Postgres).
        # Dieser Aufruf ist die Zustellung an Konsumenten NACH erfolgreichem
        # DB-Commit (siehe RepositoryPort.save_approval_and_enqueue_events).
        await self._redis.xadd(STREAM_KEY, {"data": event.model_dump_json()})

    async def subscribe(
        self, event_type: str, handler: Callable[[DomainEvent], Awaitable[None]]
    ) -> None:
        group = f"group:{event_type}"
        try:
            await self._redis.xgroup_create(STREAM_KEY, group, id="0", mkstream=True)
        except redis.ResponseError:
            pass  # Gruppe existiert bereits

        while True:
            # redis-py's Stubs bilden die tief verschachtelte XREADGROUP-Antwort
            # nicht praezise ab - Any ist hier bewusst und lokal begrenzt.
            response: Any = await self._redis.xreadgroup(
                group, "worker-1", {STREAM_KEY: ">"}, count=10, block=5000
            )
            for _stream, messages in response or []:
                for message_id, fields in messages:
                    event = DomainEvent(**json.loads(fields["data"]))
                    if event.type == event_type:
                        await handler(event)
                    await self._redis.xack(STREAM_KEY, group, message_id)
