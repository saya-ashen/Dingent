from fastapi import APIRouter, Depends, HTTPException

from dingent.core.log_manager import LogManager
from dingent.core.market_service import MarketItemCategory, MarketService
from dingent.core.plugin_manager import PluginManager
from dingent.server.api.dependencies import (
    get_log_manager,
    get_market_service,
    get_plugin_manager,
)
from dingent.server.api.schemas import MarketDownloadRequest, MarketDownloadResponse

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/metadata")
async def get_market_metadata(
    market_service: MarketService = Depends(get_market_service),
):
    """
    Get market metadata including version and item counts.
    """
    try:
        metadata = await market_service.get_market_metadata()
        return metadata.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market metadata: {e}")


@router.get("/items")
async def get_market_items(
    category: str,
    market_service: MarketService = Depends(get_market_service),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    log_manager: LogManager = Depends(get_log_manager),
):
    """
    Get list of available market items, optionally filtered by category.
    """
    try:
        category_enum = MarketItemCategory(category)
        local_plugin_versions = plugin_manager.get_installed_versions()
        items = await market_service.get_market_items(category_enum, installed_items={"plugins": local_plugin_versions})
        return [item.model_dump() for item in items]
    except Exception as e:
        log_manager.log_with_context("error", "Market fetch error", context={"category": category, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to fetch market items: {e}")


@router.post("/download", response_model=MarketDownloadResponse)
async def download_market_item(
    request: MarketDownloadRequest,
    market_service: MarketService = Depends(get_market_service),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    log_manager: LogManager = Depends(get_log_manager),
):
    """
    Download and install a market item.
    """
    try:
        result = await market_service.download_item(
            request.item_id,
            MarketItemCategory(request.category),
        )
        if result["success"]:
            if request.category == "plugin":
                plugin_manager.reload_plugins()
            return MarketDownloadResponse(**result)
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        log_manager.log_with_context(
            "error",
            "Market download error",
            context={
                "item_id": request.item_id,
                "category": request.category,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=f"Failed to download {request.category} '{request.item_id}': {e}")


@router.get("/items/{item_id}/readme")
async def get_market_item_readme(
    item_id: str,
    category: str,
    market_service: MarketService = Depends(get_market_service),
):
    """
    Get the README content for a specific market item.
    """
    try:
        category_enum = MarketItemCategory(category)
        readme_content = await market_service.get_item_readme(item_id, category_enum)
        if readme_content is None:
            raise HTTPException(status_code=404, detail=f"README not found for {category}/{item_id}")
        return {"readme": readme_content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch README for {item_id}: {e}")
