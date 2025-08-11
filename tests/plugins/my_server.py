from fastmcp import FastMCP

mcp = FastMCP(name="MyServer")


@mcp.tool()
def get_name() -> dict:
    """
    If anyone is looking for your name, this tool will return it.
    """
    return {"context": "name:Saya", "tool_outputs": {"payloads": [{"type": "markdown", "content": "name:saya"}]}}


if __name__ == "__main__":
    mcp.run(transport="http")
