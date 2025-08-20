#!/usr/bin/env python3
"""
Launch script for the Dingent Admin Dashboard.

This script provides an easy way to start the new React-style admin dashboard.
"""

import sys
import subprocess
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Start Dingent Admin Dashboard")
    parser.add_argument(
        "--port", 
        type=int, 
        default=8503, 
        help="Port to run the dashboard on (default: 8503)"
    )
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="Host to bind to (default: localhost)"
    )
    parser.add_argument(
        "--headless", 
        action="store_true", 
        help="Run in headless mode (no browser auto-open)"
    )
    
    args = parser.parse_args()
    
    # Get the path to the dashboard app
    dashboard_dir = Path(__file__).parent
    app_path = dashboard_dir / "modern_app.py"
    
    if not app_path.exists():
        print(f"❌ Dashboard app not found at {app_path}")
        sys.exit(1)
    
    # Build the streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_path),
        "--server.port", str(args.port),
        "--server.address", args.host,
    ]
    
    if args.headless:
        cmd.extend(["--server.headless", "true"])
    
    print(f"🚀 Starting Dingent Admin Dashboard...")
    print(f"📊 Dashboard will be available at: http://{args.host}:{args.port}")
    print(f"🔄 Use Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()