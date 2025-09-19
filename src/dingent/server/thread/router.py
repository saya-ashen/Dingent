from fastapi import APIRouter, Depends, FastAPI
from ..api.dependencies import dynamic_authorizer

secure_router = APIRouter(dependencies=[Depends(dynamic_authorizer)])
add_fastapi_endpoint(cast(FastAPI, secure_router), sdk, "/copilotkit")
