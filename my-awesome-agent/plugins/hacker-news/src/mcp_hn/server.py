import mcp_hn.hn as hn
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import json

DEFAULT_NUM_STORIES = 10

server = Server("hn")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get_stories",
            description="Get stories from Hacker News. The options are `top`, `new`, `ask_hn`, `show_hn` for types of stories. This doesn't include the comments. Use `get_story_info` to get the comments.",
            inputSchema={
                "type": "object",
                "properties": {
                    "story_type": {
                        "type": "string",
                        "description": "Type of stories to get, one of: `top`, `new`, `ask_hn`, `show_hn`",
                    },
                    "num_stories": {
                        "type": "integer",
                        "description": "Number of stories to get",
                    },
                },
            },
        ),
        types.Tool(
            name="get_user_info",
            description="Get user info from Hacker News, including the stories they've submitted",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "Username of the user",
                    },
                    "num_stories": {
                        "type": "integer",
                        "description": f"Number of stories to get, defaults to {DEFAULT_NUM_STORIES}",
                    },
                },
                "required": ["user_name"],
            },
        ),
        types.Tool(
            name="search_stories",
            description="Search stories from Hacker News. It is generally recommended to use simpler queries to get a broader set of results (less than 5 words). Very targetted queries may not return any results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "search_by_date": {
                        "type": "boolean",
                        "description": "Search by date, defaults to False. If this is False, then we search by relevance, then points, then number of comments.",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": f"Number of results to get, defaults to {DEFAULT_NUM_STORIES}",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_story_info",
            description="Get detailed story info from Hacker News, including the comments",
            inputSchema={
                "type": "object",
                "properties": {
                    "story_id": {
                        "type": "integer",
                        "description": "Story ID",
                    },
                },
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
    ) :
    """
    Handle tool execution requests.
    """
    if name == "get_stories":
        story_type = arguments.get("story_type", "top")
        num_stories = arguments.get("num_stories", DEFAULT_NUM_STORIES)
        output = hn.get_stories(story_type, num_stories)
        columns = list(output[0].keys())
        rows = output
        payload = {"type":"table","columns":columns, "rows":rows, "title":f"{story_type} stories"}
        structured_output = {"model_text": json.dumps(output, indent=2), "display": [payload]}
        return [types.TextContent(type="text", text=json.dumps(structured_output))]
    elif name == "search_stories":
        query = arguments.get("query")
        search_by_date = arguments.get("search_by_date", False)
        num_results = arguments.get("num_results", DEFAULT_NUM_STORIES)
        output = json.dumps(hn.search_stories(query, num_results, search_by_date), indent=2)
        return [types.TextContent(type="text", text=output)]
    elif name == "get_story_info":
        story_id = int(arguments.get("story_id"))
        output = json.dumps(hn.get_story_info(story_id), indent=2)
        return [types.TextContent(type="text", text=output)]
    elif name == "get_user_info":
        user_name = arguments.get("user_name")
        num_stories = arguments.get("num_stories", DEFAULT_NUM_STORIES)
        output = json.dumps(hn.get_user_info(user_name, num_stories), indent=2)
        return [types.TextContent(type="text", text=output)]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hn",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
