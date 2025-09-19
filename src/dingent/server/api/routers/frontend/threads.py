from typing import cast
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit.sdk import CopilotKitRemoteEndpoint
from fastapi import APIRouter, Depends, FastAPI

from dingent.server.auth.authorization import dynamic_authorizer

router = APIRouter(dependencies=[Depends(dynamic_authorizer)])


def setup_copilot_router(app: FastAPI, sdk: CopilotKitRemoteEndpoint):
    """
    Creates and configures the secure router for CopilotKit and adds it to the application.

    This function is called from within the lifespan manager after the SDK has been initialized.
    """
    print("--- Setting up CopilotKit Secure Router ---")

    add_fastapi_endpoint(cast(FastAPI, router), sdk, "/copilotkit")

    app.include_router(router, prefix="/api/v1/frontend")

    print("--- CopilotKit Secure Router has been added to the application ---")
