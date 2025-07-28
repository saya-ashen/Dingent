from dingent.engine.backend import build_agent_api, make_graph

api = build_agent_api()
graph = make_graph
if __name__ == "__main__":
    import asyncio

    async def main():
        async with graph({}) as graph:
            async for chunk in graph.astream(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": "在idog中检索柴犬（使用英文）可能会得哪些疾病（取前10个），然后在bioka中检索这些疾病可能会关联哪些biomarker",
                        }
                    ]
                },
                config={
                    "configurable": {"route": "ewas", "lang": "en-US"},
                },
                stream_mode=["debug"],
            ):
                print(chunk)

    asyncio.run(main())
