from __future__ import annotations

import re
from typing import List, Optional, cast
import uuid

from copilotkit.action import ActionDict
from copilotkit.html import generate_info_html
from copilotkit.sdk import CopilotKitContext, CopilotKitRemoteEndpoint
from copilotkit.exc import AgentExecutionException, AgentNotFoundException
from copilotkit.types import Message, MetaEvent


from fastapi import APIRouter
from fastapi.applications import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from copilotkit.integrations.fastapi import logger, body_get_or_raise, handle_execute_action, handle_get_agent_state, handler_v1, warnings

from dingent.server.copilot.async_copilotkit_remote_endpoint import AsyncCopilotKitRemoteEndpoint


async def handle_info(
    *,
    sdk: AsyncCopilotKitRemoteEndpoint,
    context: CopilotKitContext,
    as_html: bool = False,
):
    """Handle info request with FastAPI"""
    result = await sdk.info(context=context)
    if as_html:
        return HTMLResponse(content=generate_info_html(result))
    return JSONResponse(content=jsonable_encoder(result))


async def handle_execute_agent(  # pylint: disable=too-many-arguments
    *,
    sdk: CopilotKitRemoteEndpoint,
    context: CopilotKitContext,
    thread_id: str,
    name: str,
    state: dict,
    config: Optional[dict] = None,
    messages: List[Message],
    actions: List[ActionDict],
    node_name: str,
    meta_events: Optional[List[MetaEvent]] = None,
):
    """Handle continue agent execution request with FastAPI"""
    try:
        events = await sdk.execute_agent(
            context=context,
            thread_id=thread_id,
            name=name,
            node_name=node_name,
            state=state,
            config=config,
            messages=messages,
            actions=actions,
            meta_events=meta_events,
        )
        return StreamingResponse(events, media_type="application/json")
    except AgentNotFoundException as exc:
        logger.error("Agent not found: %s", exc, exc_info=True)
        return JSONResponse(content={"error": str(exc)}, status_code=404)
    except AgentExecutionException as exc:
        logger.error("Agent execution error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": str(exc)}, status_code=500)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Agent execution error: %s", exc, exc_info=True)
        return JSONResponse(content={"error": str(exc)}, status_code=500)


async def handler(request: Request, sdk: AsyncCopilotKitRemoteEndpoint):
    """Handle FastAPI request"""

    try:
        body = await request.json()
    except:  # pylint: disable=bare-except
        body = None

    path = request.path_params.get("path")
    method = request.method
    context = cast(
        CopilotKitContext,
        {
            "properties": (body or {}).get("properties", {}),
            "frontend_url": (body or {}).get("frontendUrl", None),
            "headers": request.headers,
        },
    )

    # handle / request for info endpoint
    if method in ["GET", "POST"] and path == "":
        accept_header = request.headers.get("accept", "")
        return await handle_info(
            sdk=sdk,
            context=context,
            as_html="text/html" in accept_header,
        )
    if method == "POST" and path == "info":
        return await handle_info(sdk=sdk, context=context)

    # handle /agent/name request for executing an agent
    if method == "POST" and (match := re.match(r"agent/([a-zA-Z0-9_-]+)", path)):
        name = match.group(1)
        body = body or {}

        thread_id = body.get("threadId", str(uuid.uuid4()))
        state = body.get("state", {})
        messages = body.get("messages", [])
        actions = body.get("actions", [])

        # used for LangGraph only
        node_name = body.get("nodeName")

        return await handle_execute_agent(
            sdk=sdk,
            context=context,
            thread_id=thread_id,
            node_name=node_name,
            name=name,
            state=state,
            messages=messages,
            actions=actions,
        )

    # handle /agent/name/state request for getting agent state
    if method == "POST" and (match := re.match(r"agent/([a-zA-Z0-9_-]+)/state", path)):
        name = match.group(1)
        thread_id = body_get_or_raise(body, "threadId")

        return await handle_get_agent_state(
            sdk=sdk,
            context=context,
            thread_id=thread_id,
            name=name,
        )

    # handle /action/name request for executing an action
    if method == "POST" and (match := re.match(r"action/([a-zA-Z0-9_-]+)", path)):
        name = match.group(1)
        arguments = body.get("arguments", {})

        return await handle_execute_action(
            sdk=sdk,
            context=context,
            name=name,
            arguments=arguments,
        )

    if method == "POST" and path == "actions/execute":
        name = body_get_or_raise(body, "name")
        arguments = body.get("arguments", {})

        return await handle_execute_action(
            sdk=sdk,
            context=context,
            name=name,
            arguments=arguments,
        )

    if method == "POST" and path == "agents/execute":
        thread_id = body.get("threadId")
        node_name = body.get("nodeName")
        config = body.get("config")

        name = body_get_or_raise(body, "name")
        state = body_get_or_raise(body, "state")
        messages = body_get_or_raise(body, "messages")
        actions = cast(List[ActionDict], body.get("actions", []))
        meta_events = cast(List[MetaEvent], body.get("metaEvents", []))

        return await handle_execute_agent(
            sdk=sdk,
            context=context,
            thread_id=thread_id,
            node_name=node_name,
            name=name,
            state=state,
            config=config,
            messages=messages,
            actions=actions,
            meta_events=meta_events,
        )
    if method == "POST" and path == "agents/state":
        thread_id = body_get_or_raise(body, "threadId")
        name = body_get_or_raise(body, "name")

        return await handle_get_agent_state(
            sdk=sdk,
            context=context,
            thread_id=thread_id,
            name=name,
        )

    raise HTTPException(status_code=404, detail="Not found")


def add_fastapi_endpoint(
    fastapi_app: FastAPI | APIRouter,
    sdk: AsyncCopilotKitRemoteEndpoint,
    prefix: str,
    *,
    use_thread_pool: bool = False,
    max_workers: int = 10,
):
    """Add FastAPI endpoint with configurable ThreadPoolExecutor size"""

    async def make_handler(request: Request):
        return await handler(request, sdk)

    # Ensure the prefix starts with a slash and remove trailing slashes
    normalized_prefix = "/" + prefix.strip("/")

    fastapi_app.add_api_route(
        f"{normalized_prefix}/{{path:path}}",
        make_handler,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
