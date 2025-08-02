import asyncio

from dingent.engine.mcp import create_all_mcp_servers


async def main():
    """
    Main function to parse inputs, import corresponding services as modules,
    and run them in separate processes.
    """
    mcps = await create_all_mcp_servers()

    # Create a list to store all server startup tasks.
    tasks = []
    for server_name, mcp_server in mcps.items():
        print(f"-> Scheduling '{server_name}' to run concurrently.")
        # mcp_server.run_async() is a coroutine itself.
        tasks.append(mcp_server.run_async(transport="streamable-http"))

    if not tasks:
        print("No MCP servers found to run.")
        return

    # Concurrently run all tasks in the list using asyncio.gather().
    print(f"-> Starting {len(tasks)} MCP server(s) simultaneously...")
    # The program will wait here until all tasks in gather are completed or one of them fails.
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
