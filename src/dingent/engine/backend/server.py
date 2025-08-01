import json
from typing import cast

from fastapi import FastAPI, HTTPException, Response
from loguru import logger
from mcp.types import TextResourceContents

from dingent.engine.backend.core.graph import client_resource_id_map
from dingent.engine.backend.core.mcp_manager import get_async_mcp_manager
from dingent.engine.backend.core.settings import get_settings

settings = get_settings()

assistant_id = "agent"
mcp_clients = get_async_mcp_manager(settings.mcp_servers)


def build_agent_api(**kwargs) -> FastAPI:
    app = FastAPI(**kwargs)

    @app.get("/api/resource/{resource_id}")
    async def get_resource(resource_id: str):
        client_name = client_resource_id_map.get(resource_id)
        if not client_name:
            raise HTTPException(status_code=404, detail="Resource not found")
        async with get_async_mcp_manager(settings.mcp_servers) as mcp:
            client = mcp.active_clients.get(client_name)
            if not client:
                raise HTTPException(status_code=503, detail=f"{client_name} MCP server not available")
            response = await client.read_resource(f"resource:tool_output/{resource_id}")
        logger.debug(f"Response from MCP client: {response[0]}")
        text = cast(TextResourceContents, response[0])
        json_data = json.loads(text.text)
        content = json.dumps(json_data)
        content_type = "application/json"
        return Response(content=content, media_type=content_type, headers={"Cache-Control": "public, max-age=0"})

    return app
