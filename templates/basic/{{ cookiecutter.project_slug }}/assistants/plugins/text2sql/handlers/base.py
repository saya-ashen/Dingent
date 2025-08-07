from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class DBRequest(BaseModel):
    """A structured, validated request object for the handler chain."""

    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Handler(ABC):
    """
    Abstract base handler with a helper for chain construction.
    """

    def __init__(self, **kwargs):
        # The kwargs parameter allows passing config params without breaking child classes
        self._next_handler: Handler | None = None

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        return handler

    @abstractmethod
    async def ahandle(self, request: DBRequest) -> DBRequest:
        pass

    async def _apass_to_next(self, request: DBRequest) -> DBRequest:
        if self._next_handler:
            return await self._next_handler.ahandle(request)
        return request

    @staticmethod
    def build_chain(handlers: list[Handler]) -> Handler:
        """A helper method to link a list of handlers into a chain."""
        if not handlers:
            raise ValueError("Handler list cannot be empty")

        head = handlers[0]
        current = head
        for next_handler in handlers[1:]:
            current.set_next(next_handler)
            current = next_handler
        return head
