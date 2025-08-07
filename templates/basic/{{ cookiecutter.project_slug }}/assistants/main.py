import asyncio

from dingent.engine.mcp import create_all_assistants


async def main():
    """
    Main function to parse inputs, import corresponding services as modules,
    and run them in separate processes.
    """
    assistants = await create_all_assistants()

    # Create a list to store all server startup tasks.
    tasks = []
    for assistant_name, assistant in assistants.items():
        print(f"-> Scheduling '{assistant_name}' to run concurrently.")
        # assistant.run_async() is a coroutine itself.
        tasks.append(assistant.run_async(transport="streamable-http"))

    if not tasks:
        print("No MCP servers found to run.")
        return

    # Concurrently run all tasks in the list using asyncio.gather().
    print(f"-> Starting {len(tasks)} MCP server(s) simultaneously...")
    # The program will wait here until all tasks in gather are completed or one of them fails.
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
