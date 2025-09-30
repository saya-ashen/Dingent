from fastapi import APIRouter, Depends, HTTPException


router = APIRouter(prefix="/llms", tags=["LLMs"])


@router.get("/providers")
async def list_providers():
    return []


@router.get("/models")
async def list_models():
    return []


@router.post("/models")
async def add_model():
    return {}


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    pass


@router.patch("/models/{model_id}")
async def update_model(model_id: str):
    pass


# admin only
@router.post("/providers")
async def add_provider():
    return {}


# admin only
@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str):
    pass


# admin only
@router.patch("/providers/{provider_id}")
async def update_provider(provider_id: str):
    pass
