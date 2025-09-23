from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, request: Request, with_model_text: bool = False):
    app_context = request.app.state.app_context
    resource_manager = app_context.resource_manager
    resource = resource_manager.get(artifact_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

    if not with_model_text:
        content = resource.model_dump_json(exclude={"model_text"})
    else:
        content = resource.model_dump_json()

    return Response(content=content, media_type="application/json", headers={"Cache-Control": "public, max-age=0"})
