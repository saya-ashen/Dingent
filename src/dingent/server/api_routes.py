from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from dingent.core import get_app_context
from dingent.core.log_manager import get_log_manager
from dingent.core.plugin_manager import PluginManifest
from dingent.core.settings import AssistantSettings
from dingent.core.types import (
    AssistantBase,
    AssistantCreate,
    AssistantUpdate,
    ConfigItemDetail,
    PluginUserConfig,
    Workflow,
    WorkflowCreate,
    WorkflowUpdate,
)

router = APIRouter()
app_context = get_app_context()
config_manager = app_context.config_manager
workflow_manager = app_context.workflow_manager
assistant_manager = app_context.assistant_manager
plugin_manager = app_context.plugin_manager


# ---------------------------------------------------------------------------
# Pydantic Response / Request Models (Admin)
# ---------------------------------------------------------------------------


class ToolAdminDetail(BaseModel):
    name: str
    description: str
    enabled: bool


class PluginAdminDetail(PluginUserConfig):
    tools: list[ToolAdminDetail] = Field(default_factory=list, description="该插件的工具列表")
    status: str = Field(..., description="运行状态 (active/inactive/error)")
    config: list[ConfigItemDetail] = Field(default_factory=list)


class AssistantAdminDetail(AssistantBase):
    id: str
    status: str = Field(..., description="运行状态 (active/inactive/error)")
    plugins: list[PluginAdminDetail]


class AppAdminDetail(BaseModel):
    current_workflow: str | None = None
    workflows: list[dict[str, str]] = Field(default_factory=list)
    llm: dict[str, Any]


class AddPluginRequest(BaseModel):
    plugin_name: str
    # 可选自定义初始配置（按 PluginUserConfig 结构）
    config: dict[str, Any] | None = None
    enabled: bool = True
    tools_default_enabled: bool = True


class UpdatePluginConfigRequest(BaseModel):
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    tools_default_enabled: bool | None = None
    tools: list[str] | None = None  # 覆盖工具启用列表（如果你的 PluginUserConfig 支持）


class ReplacePluginsRequest(BaseModel):
    plugins: list[PluginUserConfig]


class AssistantsBulkReplaceRequest(BaseModel):
    assistants: list[AssistantCreate | AssistantUpdate | dict]


class AssistantCreateRequest(AssistantCreate):
    pass


class AssistantUpdateRequest(AssistantUpdate):
    pass


class SetActiveWorkflowRequest(BaseModel):
    workflow_id: str


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


async def _build_plugin_admin_detail(plugin_conf: PluginUserConfig, assistant_instance) -> PluginAdminDetail:
    """
    构造单个插件的运行态详情：
      - 若实例存在：状态 active，列出当前工具
      - 若不存在：状态 inactive，仅展示配置 schema & 当前值 (masked secrets)
    """
    instance = None
    status = "inactive"
    tools_details: list[ToolAdminDetail] = []
    config_items: list[ConfigItemDetail] = []

    if assistant_instance:
        instance = assistant_instance.plugin_instances.get(plugin_conf.plugin_name or plugin_conf.name)
    if instance:
        status = getattr(instance, "status", "active")
        # 获取工具
        try:
            tool_map = await instance.list_tools()
            for t_name, t_obj in tool_map.items():
                tools_details.append(
                    ToolAdminDetail(
                        name=t_name,
                        description=getattr(t_obj, "description", "") or "No description",
                        enabled=getattr(t_obj, "enabled", True),
                    )
                )
        except Exception as e:
            status = "error"
            tools_details.append(
                ToolAdminDetail(
                    name="__error__",
                    description=f"List tools failed: {e}",
                    enabled=False,
                )
            )
        # 获取配置详情
        try:
            config_items = instance.get_config_details()
        except Exception as e:
            config_items.append(
                ConfigItemDetail(
                    name="__error__",
                    type="string",
                    description=f"Get config details failed: {e}",
                    required=False,
                    secret=False,
                    default=None,
                    value=None,
                )
            )
    else:
        # 没有实例 -> 用 manifest 填充 schema
        manifest: PluginManifest | None = plugin_manager.get_plugin_manifest(plugin_conf.plugin_name or plugin_conf.name)
        config_dict = plugin_conf.config or {}
        if manifest and manifest.config_schema:
            for schema_item in manifest.config_schema:
                val = config_dict.get(schema_item.name)
                is_secret = getattr(schema_item, "secret", False)
                if is_secret and val is not None:
                    display_val = "********"
                else:
                    display_val = val
                config_items.append(
                    ConfigItemDetail(
                        name=schema_item.name,
                        type=schema_item.type,
                        description=schema_item.description,
                        required=schema_item.required,
                        secret=is_secret,
                        default=schema_item.default,
                        value=display_val,
                    )
                )

    base_dict = plugin_conf.model_dump()
    base_dict.update(status=status, tools=tools_details, config=config_items)
    return PluginAdminDetail(**base_dict)


async def _build_assistant_admin_detail(settings: AssistantSettings, running_map: dict[str, Any]) -> AssistantAdminDetail:
    instance = running_map.get(settings.id)
    status = "active" if instance else "inactive"
    plugin_details: list[PluginAdminDetail] = []
    # 并行构建插件
    tasks = [_build_plugin_admin_detail(p, instance) for p in settings.plugins]
    if tasks:
        plugin_details = await asyncio.gather(*tasks)

    adict = settings.model_dump()
    adict.update(status=status, plugins=plugin_details)
    return AssistantAdminDetail(**adict)


def _sanitize_frontend_assistant_payload(raw: dict) -> dict:
    """
    前端传入的 assistant.plugins[].config 可能是 list[ {name,value,...} ]
    转为后端期望的 dict。
    """
    plugins = raw.get("plugins") or []
    for p in plugins:
        cfg = p.get("config")
        if isinstance(cfg, list):
            p["config"] = {item.get("name"): item.get("value") for item in cfg if item.get("name")}
    return raw


# ---------------------------------------------------------------------------
# App / LLM Settings
# ---------------------------------------------------------------------------


@router.get("/settings", response_model=AppAdminDetail)
async def get_app_settings():
    settings = config_manager.get_settings()
    workflows_summary = [{"id": wf.id, "name": wf.name} for wf in workflow_manager.list_workflows()]
    data = {
        "llm": settings.llm.model_dump(mode="json") if settings.llm else {},
        "current_workflow": workflow_manager.active_workflow_id,
        "workflows": workflows_summary,
    }
    return AppAdminDetail(**data)


@router.patch("/settings")
async def update_app_settings(payload: dict):
    """
    部分更新全局配置 (llm / current_workflow)。
    """
    patch: dict[str, Any] = {}
    if "llm" in payload:
        patch["llm"] = payload["llm"]
    if "current_workflow" in payload:
        # 仅记录；不改变运行态 active workflow（可选：同时调用 workflow_manager.set_active）
        cw = payload["current_workflow"]
        patch["current_workflow"] = cw
        if cw:
            try:
                workflow_manager.set_active(cw)
            except Exception:
                pass
        else:
            workflow_manager.clear_active()
    if not patch:
        return {"status": "noop", "message": "No updatable keys provided."}
    try:
        config_manager.update_global(patch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {e}")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Assistants
# ---------------------------------------------------------------------------


@router.get("/assistants", response_model=list[AssistantAdminDetail])
async def list_assistants_admin():
    settings_list = config_manager.list_assistants()
    running = await assistant_manager.get_all_assistants(preload=False)
    tasks = [_build_assistant_admin_detail(s, running) for s in settings_list]
    return await asyncio.gather(*tasks)


@router.post("/assistants", response_model=AssistantAdminDetail)
async def create_assistant(req: AssistantCreateRequest):
    try:
        new = config_manager.upsert_assistant(req)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 返回创建后的详情（尚未实例化 -> inactive）
    running = await assistant_manager.get_all_assistants(preload=False)
    return await _build_assistant_admin_detail(new, running)


@router.patch("/assistants/{assistant_id}", response_model=AssistantAdminDetail)
async def update_assistant(assistant_id: str, req: AssistantUpdateRequest):
    # Ensure id matches
    data = req.model_dump(exclude_unset=True)
    data["id"] = assistant_id
    try:
        updated = config_manager.upsert_assistant(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    running = await assistant_manager.get_all_assistants(preload=False)
    return await _build_assistant_admin_detail(updated, running)


@router.delete("/assistants/{assistant_id}")
async def delete_assistant(assistant_id: str):
    ok = config_manager.delete_assistant(assistant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Assistant not found")
    # AssistantManager 的 on_change 回调会关闭实例
    return {"status": "success", "message": f"Assistant {assistant_id} deleted"}


@router.put("/assistants:bulk_replace")
async def bulk_replace_assistants(req: AssistantsBulkReplaceRequest):
    """
    完整替换 assistants 列表。
    提示：这是 destructive 操作；可考虑加鉴权 / 二次确认。
    """
    raw_list = []
    for item in req.assistants:
        if isinstance(item, AssistantCreate | AssistantUpdate):
            raw = item.model_dump(exclude_unset=True)
        else:
            raw = dict(item)
        raw_list.append(_sanitize_frontend_assistant_payload(raw))

    # 事务方式写入
    try:
        with config_manager.transaction():
            # 直接替换：构造 AppSettings 新 assistants
            # 简单方式：清空后逐个 upsert
            # 为了复用校验逻辑，先清空再添加
            # 这里直接操作内部结构（或使用 import_snapshot 亦可）
            # 获取当前 settings
            settings = config_manager.get_settings()
            settings.assistants.clear()
            for a in raw_list:
                config_manager.upsert_assistant(a)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bulk replace failed: {e}")
    return {"status": "ok", "count": len(raw_list)}


# ---------------------------------------------------------------------------
# Assistant Plugin Operations (Add/Remove/Update)
# ---------------------------------------------------------------------------


@router.post("/assistants/{assistant_id}/plugins", response_model=AssistantAdminDetail)
async def add_plugin_to_assistant(assistant_id: str, req: AddPluginRequest):
    assistant_settings = config_manager.get_assistant(assistant_id)
    if not assistant_settings:
        raise HTTPException(status_code=404, detail="Assistant not found")

    manifest = plugin_manager.get_plugin_manifest(req.plugin_name)
    if not manifest:
        raise HTTPException(status_code=404, detail="Plugin not registered")

    # 防重复
    if any(p.plugin_name == req.plugin_name or p.name == req.plugin_name for p in assistant_settings.plugins):
        raise HTTPException(status_code=400, detail="Plugin already exists on assistant")

    new_plugin = PluginUserConfig(
        name=req.plugin_name,
        plugin_name=req.plugin_name,
        enabled=req.enabled,
        tools_default_enabled=req.tools_default_enabled,
        config=req.config or {},
        tools=[],  # 初始工具启用列表（若模型中表示按工具继承）
    )
    new_list = list(assistant_settings.plugins) + [new_plugin]
    config_manager.update_plugins_for_assistant(assistant_id, new_list)

    running = await assistant_manager.get_all_assistants()
    updated_settings = config_manager.get_assistant(assistant_id)
    return await _build_assistant_admin_detail(updated_settings, running)


@router.patch("/assistants/{assistant_id}/plugins/{plugin_name}", response_model=AssistantAdminDetail)
async def update_plugin_on_assistant(assistant_id: str, plugin_name: str, req: UpdatePluginConfigRequest):
    settings = config_manager.get_assistant(assistant_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Assistant not found")

    updated_plugins: list[PluginUserConfig] = []
    found = False
    for p in settings.plugins:
        if p.plugin_name == plugin_name or p.name == plugin_name:
            found = True
            data = p.model_dump(exclude_unset=True)
            if req.config is not None:
                data["config"] = req.config
            if req.enabled is not None:
                data["enabled"] = req.enabled
            if req.tools_default_enabled is not None:
                data["tools_default_enabled"] = req.tools_default_enabled
            if req.tools is not None:
                data["tools"] = req.tools
            p_new = PluginUserConfig.model_validate(data)
            updated_plugins.append(p_new)
        else:
            updated_plugins.append(p)
    if not found:
        raise HTTPException(status_code=404, detail="Plugin not found on assistant")

    config_manager.update_plugins_for_assistant(assistant_id, updated_plugins)
    running = await assistant_manager.get_all_assistants()
    updated_settings = config_manager.get_assistant(assistant_id)
    return await _build_assistant_admin_detail(updated_settings, running)


@router.delete("/assistants/{assistant_id}/plugins/{plugin_name}", response_model=AssistantAdminDetail)
async def remove_plugin_from_assistant(assistant_id: str, plugin_name: str):
    settings = config_manager.get_assistant(assistant_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Assistant not found")

    filtered = [p for p in settings.plugins if not (p.plugin_name == plugin_name or p.name == plugin_name)]
    if len(filtered) == len(settings.plugins):
        raise HTTPException(status_code=404, detail="Plugin not found on assistant")

    config_manager.update_plugins_for_assistant(assistant_id, filtered)
    running = await assistant_manager.get_all_assistants()
    updated_settings = config_manager.get_assistant(assistant_id)
    return await _build_assistant_admin_detail(updated_settings, running)


# ---------------------------------------------------------------------------
# Plugins Catalog
# ---------------------------------------------------------------------------


@router.get("/plugins", response_model=list[PluginManifest])
async def list_available_plugins():
    return list(plugin_manager.list_plugins().values())


@router.delete("/plugins/{plugin_name}")
async def remove_plugin_global(plugin_name: str):
    """
    全局移除插件（仅在 plugin_manager 中卸载或删除物理目录，实际实现视项目而定）。
    这里简单调用 plugin_manager.remove_plugin，如果需要同步 assistants 的配置，
    需额外遍历并删除相关 plugin config（可在此实现或外部任务）。
    """
    try:
        plugin_manager.remove_plugin(plugin_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # 可选：同步移除所有助手配置中的该插件
    assistants = config_manager.list_assistants()
    changed = False
    for a in assistants:
        new_plugins = [p for p in a.plugins if not (p.plugin_name == plugin_name or p.name == plugin_name)]
        if len(new_plugins) != len(a.plugins):
            config_manager.update_plugins_for_assistant(a.id, new_plugins)
            changed = True
    return {"status": "success", "assistants_updated": changed}


# ---------------------------------------------------------------------------
# Logs (保持原逻辑)
# ---------------------------------------------------------------------------


@router.get("/logs")
async def logs(level: str | None = None, module: str | None = None, limit: int | None = None, search: str | None = None):
    try:
        lm = get_log_manager()
        entries = lm.get_logs(level=level, module=module, limit=limit, search=search)
        return [e.to_dict() for e in entries]
    except Exception:
        return []


@router.get("/logs/stats")
async def log_stats():
    try:
        lm = get_log_manager()
        return lm.get_log_stats()
    except Exception:
        raise HTTPException(status_code=404)


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


@router.get("/workflows", response_model=list[Workflow])
async def list_workflows():
    return workflow_manager.list_workflows()


@router.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    wf = workflow_manager.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("/workflows", response_model=Workflow)
async def create_workflow(wf_create: WorkflowCreate, make_active: bool = False):
    try:
        wf = workflow_manager.create_workflow(wf_create, make_active=make_active)
        return wf
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/workflows/{workflow_id}", response_model=Workflow)
async def replace_workflow(workflow_id: str, workflow: Workflow):
    if workflow.id != workflow_id:
        raise HTTPException(status_code=400, detail="Workflow ID mismatch")
    try:
        return workflow_manager.save_workflow(workflow)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/workflows/{workflow_id}", response_model=Workflow)
async def patch_workflow(workflow_id: str, patch: WorkflowUpdate):
    try:
        return workflow_manager.update_workflow(workflow_id, patch)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    ok = workflow_manager.delete_workflow(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "message": f"Workflow {workflow_id} deleted"}


@router.post("/workflows/{workflow_id}/activate")
async def activate_workflow(workflow_id: str):
    try:
        workflow_manager.set_active(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "success", "current_workflow": workflow_id}


@router.get("/workflows/active")
async def get_active_workflow():
    return {"current_workflow": workflow_manager.active_workflow_id}


# ---------------------------------------------------------------------------
# Optional: runtime instantiation endpoint (if needed)
# ---------------------------------------------------------------------------


@router.post("/workflows/{workflow_id}/instantiate")
async def instantiate_workflow(workflow_id: str):
    """
    根据 workflow 构建（或重用）assistant 实例并设置 destinations。
    仅在需要手动触发时使用；否则可在激活时自动调用。
    """
    try:
        # 这里调用 workflow_manager.instantiate_workflow_assistants (若保留该方法)。
        if not hasattr(workflow_manager, "instantiate_workflow_assistants"):
            raise HTTPException(status_code=400, detail="Runtime instantiation not supported in current build.")
        result = await workflow_manager.instantiate_workflow_assistants(workflow_id)
        return {
            "status": "success",
            "assistants": {name: {"destinations": inst.destinations} for name, inst in result.items()},
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------


class MarketMetadata(BaseModel):
    version: str
    updated_at: str
    categories: dict[str, int]


class MarketItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    version: str | None = None
    author: str | None = None
    category: str  # "plugin" | "assistant" | "workflow"
    tags: list[str] = Field(default_factory=list)
    license: str | None = None
    readme: str | None = None
    downloads: int | None = None
    rating: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MarketDownloadRequest(BaseModel):
    item_id: str
    category: str  # "plugin" | "assistant" | "workflow"


class MarketDownloadResponse(BaseModel):
    success: bool
    message: str
    installed_path: str | None = None


@router.get("/market/metadata", response_model=MarketMetadata)
async def get_market_metadata():
    """
    Get market metadata including version and item counts.
    """
    try:
        # In a real implementation, this would fetch from the dingent-market repository
        # For now, return mock data
        return MarketMetadata(
            version="1.0.0",
            updated_at="2024-08-29T00:00:00Z",
            categories={
                "plugins": 15,
                "assistants": 8,
                "workflows": 5
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market metadata: {e}")


@router.get("/market/items", response_model=list[MarketItem])
async def get_market_items(category: str | None = None):
    """
    Get list of available market items, optionally filtered by category.
    """
    try:
        # Mock data - in real implementation, this would fetch from GitHub API
        items = [
            MarketItem(
                id="awesome-calculator",
                name="Awesome Calculator",
                description="A powerful calculator plugin with advanced mathematical functions",
                version="1.2.0",
                author="Community",
                category="plugin",
                tags=["math", "calculator", "utility"],
                license="MIT",
                downloads=1250,
                rating=4.5,
                created_at="2024-01-15T10:00:00Z",
                updated_at="2024-08-15T14:30:00Z"
            ),
            MarketItem(
                id="daily-report",
                name="Daily Report Workflow",
                description="Automated daily reporting workflow for data analysis",
                version="2.1.0",
                author="Community",
                category="workflow",
                tags=["reporting", "automation", "daily"],
                license="MIT",
                downloads=890,
                rating=4.8,
                created_at="2024-02-20T09:00:00Z",
                updated_at="2024-08-20T11:15:00Z"
            ),
            MarketItem(
                id="support-assistant",
                name="Customer Support Assistant",
                description="Pre-configured assistant for customer support scenarios",
                version="1.0.0",
                author="Community",
                category="assistant",
                tags=["support", "customer", "service"],
                license="MIT",
                downloads=567,
                rating=4.2,
                created_at="2024-03-10T16:00:00Z",
                updated_at="2024-07-25T13:45:00Z"
            )
        ]
        
        if category:
            items = [item for item in items if item.category == category]
        
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market items: {e}")


@router.post("/market/download", response_model=MarketDownloadResponse)
async def download_market_item(request: MarketDownloadRequest):
    """
    Download and install a market item.
    """
    try:
        # TODO: Implement actual download logic
        # This would:
        # 1. Fetch the item from the dingent-market repository
        # 2. Download the files to the appropriate directory
        # 3. Register the item with the appropriate manager
        
        # For now, return a mock response
        return MarketDownloadResponse(
            success=True,
            message=f"Successfully downloaded {request.category}: {request.item_id}",
            installed_path=f"./{request.category}s/{request.item_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download {request.category} '{request.item_id}': {e}")


@router.get("/market/items/{item_id}/readme", response_model=dict[str, str])
async def get_market_item_readme(item_id: str):
    """
    Get the README content for a specific market item.
    """
    try:
        # TODO: Implement actual README fetching from GitHub
        # For now, return mock content
        return {
            "readme": f"# {item_id}\n\nThis is a mock README for {item_id}.\n\n## Installation\n\nThis item has been successfully installed from the Dingent Market."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch README for {item_id}: {e}")
