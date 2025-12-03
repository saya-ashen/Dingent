from typing import Annotated

from pydantic import Field

from dingent.engine.plugins import BaseTool
from dingent.engine.plugins.types import TablePayload, ToolOutput

from .settings import Settings


class Greeter(BaseTool):
    """A tool that uses the Text2SqlAgent to answer questions from a database."""

    def __init__(
        self,
        config: Settings,
        **kwargs,
    ):
        super().__init__(config, **kwargs)

    async def tool_run(
        self,
        target: Annotated[str, Field(description="Say hello to this person.")],
    ) -> dict:
        """Use the tool."""
        artifact_ids = []
        artifact_ids.append(
            self.resource_manager.register(ToolOutput(type="greeter", payload=TablePayload(columns=["greeter", "target"], rows=[{"greeter": self.name, "target": target}])))
        )
        return {"context": f"{self.name} is saying hello to {target}", "artifact_ids": artifact_ids, "source": "greeter"}
