import asyncio
import json
from typing import cast

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.requests import Request
from fastapi.responses import StreamingResponse
from langgraph_sdk import get_client
from mcp.types import TextResourceContents
from pydantic import BaseModel

from backend.core.mcp_manager import AsyncMCPManager, get_async_mcp_manager
from backend.core.settings import get_settings
from backend.core.types import AgentStreamResponse, StreamEndData, StreamEndEvent

settings = get_settings()

client = get_client(url="http://localhost:8000")
assistant_id = "agent"
mcp_clients = get_async_mcp_manager(settings.mcp_servers)
from backend.core.graph import client_resource_id_map


async def get_language(x_app_language: str | None = Header(None, alias="X-App-Language")) -> str:
    """
    从请求头 X-App-Language 中获取语言。
    如果没有提供，则返回一个默认值。
    """
    return x_app_language or "en-US"  # 如果前端没传，默认为 'en'


def get_real_ip(request: Request) -> str:
    """
    获取真实客户端IP，优先从 X-Forwarded-For 头获取。
    这对于部署在反向代理（如Nginx）后的应用至关重要。
    """
    # X-Forwarded-For 的值可能是一个列表: "client, proxy1, proxy2"
    # 第一个通常是真实的客户端IP
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    # 如果没有代理，直接使用 request.client.host
    return request.client.host


app = FastAPI()


class ChatRequest(BaseModel):
    user_input: str
    route: str | None = None


class Chat(BaseModel):
    id: str


@app.post("/api/chats/{chat_id}")
async def stream_chat(
    chat_id: str, request: ChatRequest, lang: str = Depends(get_language), ip_info=Depends(get_real_ip)
):
    print(f"Streaming chat for chat_id: {chat_id}, route: {request.route}, lang: {lang},ip: {ip_info}")
    # 定义 keep-alive 的时间间隔（秒）
    KEEPALIVE_INTERVAL = 10
    # 定义 keep-alive 信号的内容 (标准的 SSE 注释)
    KEEPALIVE_SIGNAL = ":\n\n"
    # 定义一个特殊的信号，用于表示数据流结束
    SENTINEL = object()

    async def stream_response_chunks():
        # 创建一个异步队列来在任务间传递数据
        queue = asyncio.Queue()

        # 1. 生产者任务：从外部服务获取数据并放入队列
        async def producer():
            try:
                print(f"Starting producer for chat_id: {chat_id}, route: {request.route}, lang: {lang}")
                # 您的原始循环
                async for chunk in client.runs.stream(
                    thread_id=chat_id,
                    assistant_id=assistant_id,
                    input={"messages": [{"role": "user", "content": request.user_input}]},
                    stream_mode="custom",
                    stream_subgraphs=True,
                    config={"configurable": {"route": request.route, "lang": lang, "ip_info": ip_info}},
                ):
                    if "custom" not in chunk.event:
                        continue
                    await queue.put(json.dumps(chunk.data) + "\n")
            except Exception as e:
                print(f"Error in producer: {e}")

            finally:
                # 确保无论如何（即使有错误），我们都发出结束信号
                await queue.put(SENTINEL)

        # 启动生产者任务，它将开始在后台填充队列
        producer_task = asyncio.create_task(producer())

        # 2. 消费者逻辑：从队列中获取数据，带超时处理
        while True:
            try:
                # 等待队列中的下一个项目，但最多只等 KEEPALIVE_INTERVAL 秒
                chunk = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_INTERVAL)

                if chunk is SENTINEL:
                    # 如果收到结束信号，则跳出循环
                    break

                # 成功获取到数据块，将其产出
                yield chunk

            except TimeoutError:
                # 如果等待超时，说明连接空闲，产出 keep-alive 信号
                yield KEEPALIVE_SIGNAL

        # 等待生产者任务彻底完成（以防万一有未处理的异常）
        await producer_task

        # 最后产出结束事件
        end_event = StreamEndEvent(event_type="stream_end", data=StreamEndData(final_state="success"))
        yield AgentStreamResponse(root=end_event).model_dump_json()

    headers = {"Content-Type": "text/event-stream", "Cache-Control": "no-cache"}
    return StreamingResponse(stream_response_chunks(), headers=headers, media_type="text/event-stream")


@app.post("/api/chats", response_model=Chat)
async def create_chat():
    thread = await client.threads.create()
    return Chat(id=thread["thread_id"])


async def process_server(client_manager: AsyncMCPManager, lang: str = "en-US"):
    """Processes a single server configuration asynchronously."""
    available_routes = []
    clients = client_manager.active_clients
    for client in clients.values():
        server_info = (await client.read_resource(f"info://server_info/{lang}"))[0].text  # type: ignore
        server_info = json.loads(server_info)
        available_routes.append(
            {"value": server_info["server_id"], "tools": server_info["tools_info"], "label": server_info["server_name"]}
        )

    return available_routes

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
    text = cast(TextResourceContents, response[0])
    json_data = json.loads(text.text)
    content = json.dumps(json_data)
    content_type = "application/json"
    return Response(content=content, media_type=content_type, headers={"Cache-Control": "public, max-age=0"})
