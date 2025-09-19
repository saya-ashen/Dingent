import os
import uvicorn
from .app import create_app, base_lifespan

IS_DEV_MODE = os.getenv("DINGENT_DEV")

# Create the base app
app = create_app()

if not IS_DEV_MODE:
    print("--- RUN MODE DETECTED: Applying CopilotKit extensions. ---")
    # Import and apply CopilotKit extensions
    from .copilot.lifespan import create_extended_lifespan

    extended_lifespan = create_extended_lifespan(base_lifespan)
    app.router.lifespan_context = extended_lifespan
    from .core.middleware import DebugRequestMiddleware

    app.add_middleware(DebugRequestMiddleware)

    def start():
        """Launches the Uvicorn server."""
        port = int(os.getenv("PORT", "8000"))
        uvicorn.run(
            "dingent.server.main:app",
            host="0.0.0.0",
            port=port,
        )

elif IS_DEV_MODE:
    print("--- DEV MODE DETECTED: Running base application. ---")
    from .core.middleware import DebugRequestMiddleware

    app.add_middleware(DebugRequestMiddleware)
