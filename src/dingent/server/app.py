from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dingent.core.context import initialize_app_context
from .api.router import api_router


@asynccontextmanager
async def base_lifespan(app: FastAPI):
    """The original, base lifespan for the application."""
    print("--- Application Startup (Base) ---")
    app.state.app_context = initialize_app_context()
    yield
    print("--- Application Shutdown (Base) ---")
    await app.state.app_context.close()


def create_app() -> FastAPI:
    """Creates and configures the base FastAPI application."""
    app = FastAPI(lifespan=base_lifespan, title="Dingent API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3001", "http://localhost:5173"],  # Be specific
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    return app
