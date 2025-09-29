from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dingent.core.context import initialize_app_context
from .api import api_router


@asynccontextmanager
async def base_lifespan(app: FastAPI):
    """The original, base lifespan for the application."""
    print("--- Application Startup (Base) ---")
    app.state.app_context = initialize_app_context()
    yield
    print("--- Application Shutdown (Base) ---")
    await app.state.app_context.close_async_components()


def create_app() -> FastAPI:
    """Creates and configures the base FastAPI application."""
    app = FastAPI(lifespan=base_lifespan, title="Dingent API")

    # CORS middleware
    origins = [
        "http://localhost",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "https://smith.langchain.com",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    # app.include_router(admin_router)  # Admin SPA routes

    return app
