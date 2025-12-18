import os

import uvicorn

from .app import base_lifespan, create_app
from .copilot.lifespan import create_extended_lifespan

app = create_app()


extended_lifespan = create_extended_lifespan(base_lifespan)
app.router.lifespan_context = extended_lifespan


def start():
    """Launches the Uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "dingent.server.main:app",
        host="0.0.0.0",
        port=port,
    )
