from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from vital_mapper.domain.events import DomainEvent


class EventBusPort(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...

    @abstractmethod
    async def subscribe(
        self, event_type: str, handler: Callable[[DomainEvent], Awaitable[None]]
    ) -> None: ...
