import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dingent.core import Assistant, get_assistant_manager, get_config_manager, get_plugin_manager
from dingent.core.log_manager import get_log_manager
from dingent.core.plugin_manager import PluginManifest
from dingent.core.types import AssistantBase, AssistantCreate, ConfigItemDetail, PluginUserConfig, Workflow, WorkflowCreate, WorkflowUpdate
from dingent.core.workflow_manager import get_workflow_manager

router = APIRouter()
config_manager = get_config_manager()
assistant_manager = get_assistant_manager()
plugin_manager = get_plugin_manager()
workflow_manager = get_workflow_manager()


class ToolAdminDetail(BaseModel):
    name: str
    description: str
    enabled: bool


class PluginAdminDetail(PluginUserConfig):
    # 增加 tools 字段来存放工具的详细信息
    tools: list[ToolAdminDetail] = Field(default_factory=list, description="该插件的工具列表")
    status: str = Field(..., description="运行状态 (e.g., 'active', 'inactive', 'error')")
    config: list[ConfigItemDetail] = []


class AssistantAdminDetail(AssistantBase):
    id: str = Field(..., description="助手的唯一标识符")
    status: str = Field(..., description="运行状态 (e.g., 'active', 'inactive', 'error')")
    # plugins 字段的类型应为优化后的 PluginAdminDetail
    plugins: list[PluginAdminDetail] = Field(..., description="该助手的插件配置")


class AppAdminDetail(BaseModel):
    current_workflow: str | None = None
    workflows: list[dict[str, str]] = Field(default_factory=list)
    llm: dict[str, Any]


class AddPluginRequest(BaseModel):
    plugin_name: str
    config: PluginUserConfig | None = None


# --- 1. 辅助函数：处理单个插件 ---
async def _build_plugin_admin_detail(plugin_config: PluginUserConfig, plugin_instance):
    """根据插件配置和其所属的助手实例，构建带有状态的插件详情。"""

    tools_details = []
    plugin_status = plugin_instance.status
    tool_instances = await plugin_instance.list_tools()
    tools_details = [ToolAdminDetail(name=name, description=tool.description or "No description", enabled=tool.enabled) for name, tool in tool_instances.items()]

    config_details = plugin_instance.get_config_details()

    plugin_admin_detail_dict = plugin_config.model_dump()
    plugin_admin_detail_dict.update(status=plugin_status, tools=tools_details, config=config_details)
    return PluginAdminDetail(**plugin_admin_detail_dict)


# --- 2. 辅助函数：处理单个助手 ---
async def _build_assistant_admin_detail(assistant_config: AssistantAdminDetail, running_assistants: dict[str, Assistant]):
    """根据助手配置和所有正在运行的助手实例，构建带有状态的助手详情。"""

    assistant_instance = running_assistants.get(assistant_config.id)
    assistant_status = "active" if assistant_instance else "inactive"

    plugin_details = []
    if assistant_instance:
        for plugin_config in assistant_config.plugins:
            plugin_instance = assistant_instance.plugin_instances.get(plugin_config.name)
            if plugin_instance:
                plugin_detail = await _build_plugin_admin_detail(plugin_config, plugin_instance)
            else:
                config_details = []
                plugin_mainifest = plugin_manager.get_plugin_manifest(plugin_config.name)
                assert plugin_mainifest
                config = plugin_config.config or {}
                for schema_item in plugin_mainifest.config_schema or []:
                    current_value = config.get(schema_item.name)

                    # For secrets, we should not expose the actual value.
                    # We can return a placeholder or just indicate that it's set.
                    # Here, we return a placeholder if the value is set.
                    is_secret = getattr(schema_item, "secret", False)
                    if is_secret and current_value is not None:
                        display_value = "********"  # Placeholder for secrets
                    else:
                        display_value = current_value

                    item_detail = ConfigItemDetail(
                        name=schema_item.name,
                        type=schema_item.type,
                        description=schema_item.description,
                        required=schema_item.required,
                        secret=is_secret,
                        default=schema_item.default,
                        value=display_value,  # Use the placeholder-aware value
                    )
                    config_details.append(item_detail)
                plugin_detail = PluginAdminDetail(**plugin_config.model_dump(exclude=["tools", "config"]), config=config_details, status="inactive")
            plugin_details.append(plugin_detail)

    assistant_admin_detail_dict = assistant_config.model_dump()

    assistant_admin_detail_dict.update(status=assistant_status, plugins=plugin_details)
    return AssistantAdminDetail(**assistant_admin_detail_dict)


@router.get("/settings", response_model=AppAdminDetail)
async def get_app_settings():
    """
    获取应用的核心配置（不包括助手列表）。
    """
    app_config = config_manager.get_config()
    app_settings_dict = app_config.model_dump(exclude={"assistants", "workflows"})
    workflows = app_config.workflows or []
    workflows_summary = [{"id": wf.id, "name": wf.name} for wf in workflows]
    app_settings_dict["workflows"] = workflows_summary
    return AppAdminDetail(**app_settings_dict)


@router.patch("/settings")
async def update_app_settings(settings: dict):
    """
    更新应用的核心配置（例如 LLM 设置）。
    """
    # Create a partial config dictionary to update
    current_workflow_id = settings.get("current_workflow")
    config_to_update = {
        "llm": settings.get("llm"),
        "current_workflow": current_workflow_id,
    }

    config_manager.update_config(config_to_update, True)
    config_manager.save_config()
    await assistant_manager.rebuild()  # Rebuild might be needed if LLM settings change
    return {"status": "ok", "message": "App settings updated successfully."}


@router.get("/assistants", response_model=list[AssistantAdminDetail])
async def get_all_assistants_with_status():
    """
    获取所有助手的完整配置列表，并注入实时运行状态。
    """
    app_config = config_manager.get_config()
    running_assistants = await assistant_manager.get_assistants()

    # Concurrently build the details for all assistants
    assistant_tasks = [_build_assistant_admin_detail(a_config, running_assistants) for a_config in app_config.assistants]
    assistant_admin_details = await asyncio.gather(*assistant_tasks)

    return assistant_admin_details


@router.put("/assistants")
async def update_assistants_config(assistants_config: list[dict]):
    """
    接收完整的助手列表并更新配置。
    """
    # Pre-process the plugin config from the frontend format (list of dicts)
    # back to the backend format (dict of key-value pairs).
    for assistant in assistants_config:
        for plugin in assistant.get("plugins", []):
            config_list = plugin.get("config")

            if isinstance(config_list, list):
                simple_config_dict = {item.get("name"): item.get("value") for item in config_list if item.get("name") is not None}
                plugin["config"] = simple_config_dict

    # Update only the 'assistants' part of the main config
    config_manager.update_config({"assistants": assistants_config})
    config_manager.save_config()
    await assistant_manager.rebuild()
    return {"status": "ok", "message": "Assistants configuration updated successfully."}


@router.post("/assistants")
async def add_assistant(assistant_config: AssistantCreate):
    config_manager.add_assistant(assistant_config)
    config_manager.save_config()
    await assistant_manager.rebuild()


@router.delete("/assistants/{assistant_id}")
async def remove_assistant(assistant_id: str):
    config_manager.remove_assistant(assistant_id)
    config_manager.save_config()
    await assistant_manager.rebuild()


@router.get("/plugins", response_model=list[PluginManifest])
async def list_available_plugins():
    """
    Scans the plugin directory and returns a list of all valid plugin manifests.
    """
    plugin_manager = get_plugin_manager()
    # PluginManager stores plugins in a dict, so we return the values
    return list(plugin_manager.list_plugins().values())


@router.delete("/plugins/{plugin_name}")
async def remove_plugin_endpoint(plugin_name: str):
    """
    Removes a plugin's directory and unregisters it from the manager.
    NOTE: For security, this assumes a simple directory removal.
          In a production system, you might want more robust checks
          or a "soft delete" mechanism.
    """
    plugin_manager = get_plugin_manager()

    try:
        plugin_manager.remove_plugin(plugin_name)
        return {"status": "success", "message": f"Removal request for '{plugin_name}' processed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assistants/{assistant_id}/plugins")
async def add_plugin_to_assistant(assistant_id: str, request_body: AddPluginRequest):
    """
    Adds a plugin to an existing assistant.
    """
    assistant = config_manager.get_assistant_by_id(assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail=f"Assistant {assistant_id} not found")

    plugin_name = request_body.plugin_name
    try:
        config_manager.add_plugin_config_to_assistant(assistant_id, plugin_name)
        config_manager.save_config()
        await assistant_manager.rebuild()
        return {"status": "success", "message": f"Plugin '{plugin_name}' added to assistant '{assistant_id}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/assistants/{assistant_id}/plugins/{plugin_name}")
async def remove_plugin_from_assistant(assistant_id: str, plugin_name: str):
    """
    Removes a plugin configuration from an existing assistant.
    """
    try:
        config_manager.remove_plugin_from_assistant(assistant_id, plugin_name)
        config_manager.save_config()
        await assistant_manager.rebuild()
        return {"status": "success", "message": f"Plugin '{plugin_name}' removed from assistant '{assistant_id}'."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Catch-all for other potential errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.get("/logs")
async def logs(level: str | None = None, module: str | None = None, limit: int | None = None, search: str | None = None):
    try:
        log_manager = get_log_manager()
        logs = log_manager.get_logs(level=level, module=module, limit=limit, search=search)
        return [log.to_dict() for log in logs]
    except Exception:
        return []


@router.get("/logs/stats")
async def log_statistics():
    try:
        log_manager = get_log_manager()
        return log_manager.get_log_stats()
    except Exception:
        raise HTTPException(404)


# --- Workflows ---


@router.get("/workflows", response_model=list[Workflow])
async def get_all_workflows():
    """
    Get all workflows.
    """
    return workflow_manager.get_workflows()


@router.get("/workflows/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    """
    Get a specific workflow by ID.
    """
    workflow = workflow_manager.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    return workflow


@router.post("/workflows", response_model=Workflow)
async def create_workflow(workflow_create: WorkflowCreate):
    """
    Create a new workflow.
    """
    try:
        workflow = workflow_manager.create_workflow(workflow_create)
        config_manager.reload()
        return workflow
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workflows/{workflow_id}", response_model=Workflow)
async def save_workflow(workflow_id: str, workflow: Workflow):
    """
    Save/update a complete workflow.
    """
    if workflow.id != workflow_id:
        raise HTTPException(status_code=400, detail="Workflow ID mismatch")
    try:
        saved_workflow = workflow_manager.save_workflow(workflow)
        config_manager.reload()
        return saved_workflow
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/workflows/{workflow_id}", response_model=Workflow)
async def update_workflow(workflow_id: str, workflow_update: WorkflowUpdate):
    """
    Partially update a workflow.
    """
    workflow = workflow_manager.update_workflow(workflow_id, workflow_update)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    config_manager.reload()
    return workflow


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """
    Delete a workflow.
    """
    success = workflow_manager.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    return {"status": "success", "message": f"Workflow {workflow_id} deleted successfully"}
