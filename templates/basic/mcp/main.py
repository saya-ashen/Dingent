import argparse
import multiprocessing
import sys

from dingent.engine import create_all_mcp_server


async def main():
    """
    主函数，用于解析输入，并将相应的服务作为模块导入，在独立的进程中运行。
    """
    parser = argparse.ArgumentParser(
        description="A main entry point to launch multiple server applications in parallel processes.",
        epilog="Example: python main.py --server-ids service_a service_b",  # Epilog也更新一下
    )

    parser.add_argument(
        "-s",
        "--server-ids",
        default=[],
        nargs="+",
        help="The names of the servers to run (e.g., 'service_a' 'service_b').",
    )

    args = parser.parse_args()
    mcps = await create_all_mcp_server(args.server_ids)

    # --- 2. 准备并启动所有指定的进程 ---
    processes = []  # Changed from 'threads' to 'processes'

    print("--- Preparing to launch services in processes... ---")

    for server_name, mcp_server in mcps.items():
        try:
            process = multiprocessing.Process(
                target=mcp_server.run,
                kwargs={"transport": "streamable-http"},
                name=server_name,
            )

            print(f"-> Launching '{server_name}' in a new process.")
            process.start()
            processes.append((process, server_name))

        except Exception as e:
            print(f"[ERROR] An unexpected error occurred while launching '{server_name}': {e}", file=sys.stderr)

    if not processes:
        print("\nNo valid services were launched. Exiting.")
        sys.exit(1)

    print(f"\n--- {len(processes)} service(s) launched successfully. Running in parallel. ---")
    print("Press Ctrl+C to signal termination to all services.")

    # --- 3. 等待所有进程完成，并处理退出 ---
    try:
        for process, server_name in processes:
            process.join()

    except KeyboardInterrupt:
        print("\n\n--- Interruption received! Signaling all services to terminate... ---")
        for process, server_name in processes:
            print(f"-> Terminating '{server_name}'...")
            process.terminate()  # Send a SIGTERM signal
            process.join()

        print("\n--- All services terminated. ---")
        sys.exit(130)

    print("\n--- All services have completed their tasks. ---")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
