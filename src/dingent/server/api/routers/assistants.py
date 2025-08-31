import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from dingent.core.assistant_manager import AssistantManager
from dingent.core.config_manager import ConfigManager
from dingent.core.plugin_manager import PluginManager, PluginManifest, _create_dynamic_config_model
from dingent.core.settings import AssistantSettings
from dingent.core.types import (
    AssistantCreate,
    AssistantUpdate,
    ConfigItemDetail,
    PluginUserConfig,
)
from dingent.server.api.dependencies import (
    get_assistant_manager,
    get_config_manager,
    get_plugin_manager,
)
from dingent.server.api.schemas import (
    AddPluginRequest,
    AssistantAdminDetail,
    AssistantCreateRequest,
    AssistantsBulkReplaceRequest,
    AssistantUpdateRequest,
    PluginAdminDetail,
    ToolAdminDetail,
    UpdatePluginConfigRequest,
)

router = APIRouter(prefix="/assistants", tags=["Assistants"])


async def _build_plugin_admin_detail(plugin_conf: PluginUserConfig, assistant_instance: Any, plugin_manager: PluginManager) -> PluginAdminDetail:
    instance = None
    status = "inactive"
    tools_details: list[ToolAdminDetail] = []
    config_items: list[ConfigItemDetail] = []
    manifest: PluginManifest | None = plugin_manager.get_plugin_manifest(plugin_conf.plugin_id)
    if not manifest:
        raise ValueError(f"Plugin manifest not found for id: {plugin_conf.plugin_id}")

    if assistant_instance:
        instance = assistant_instance.plugin_instances.get(plugin_conf.plugin_id)
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
    base_dict.update(status=status, tools=tools_details, config=config_items, name=manifest.name)
    return PluginAdminDetail(**base_dict)


async def _build_assistant_admin_detail(settings: AssistantSettings, running_map: dict[str, Any], plugin_manager: PluginManager) -> AssistantAdminDetail:
    instance = running_map.get(settings.id)
    status = "active" if instance else "inactive"

    tasks = [_build_plugin_admin_detail(p, instance, plugin_manager) for p in settings.plugins]
    plugin_details = await asyncio.gather(*tasks) if tasks else []

    adict = settings.model_dump()
    adict.update(status=status, plugins=list(plugin_details))
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


@router.get("", response_model=list[AssistantAdminDetail])
async def list_assistants(
    config_manager: ConfigManager = Depends(get_config_manager),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    settings_list = config_manager.list_assistants()
    running = await assistant_manager.get_all_assistants(preload=True)
    tasks = [_build_assistant_admin_detail(s, running, plugin_manager) for s in settings_list]
    response_data = await asyncio.gather(*tasks)
    return response_data


@router.post("", response_model=AssistantAdminDetail)
async def create_assistant(
    req: AssistantCreateRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    try:
        new = config_manager.upsert_assistant(req)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 返回创建后的详情（尚未实例化 -> inactive）
    running = await assistant_manager.get_all_assistants(preload=False)
    return await _build_assistant_admin_detail(new, running, plugin_manager)


@router.patch("/{assistant_id}", response_model=AssistantAdminDetail)
async def update_assistant(
    assistant_id: str,
    req: AssistantUpdateRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    # Ensure id matches
    plugins = req.plugins
    for plugin in plugins or []:
        plugin_id = plugin.plugin_id
        plugin_manifest = plugin_manager.get_plugin_manifest(plugin_id)
        plugin_config_schemas = (plugin_manifest.config_schema if plugin_manifest else []) or []
        if not plugin_manifest or not plugin_config_schemas or not plugin_manifest.config_schema:
            continue
        DynamicConfigModel = _create_dynamic_config_model(plugin_manifest.name, plugin_manifest.config_schema)
        plugin.config = DynamicConfigModel.model_validate(plugin.config)
    data = req.model_dump(exclude_unset=True)
    data["id"] = assistant_id
    try:
        updated = config_manager.upsert_assistant(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    running = await assistant_manager.get_all_assistants(preload=False)
    return await _build_assistant_admin_detail(updated, running, plugin_manager)


@router.put("/assistants:bulk_replace")
async def bulk_replace_assistants(
    req: AssistantsBulkReplaceRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
):
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


@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: str,
    config_manager: ConfigManager = Depends(get_config_manager),
):
    ok = config_manager.delete_assistant(assistant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return {"status": "success", "message": f"Assistant {assistant_id} deleted"}


@router.post("/{assistant_id}/plugins", response_model=AssistantAdminDetail)
async def add_plugin_to_assistant(
    assistant_id: str,
    req: AddPluginRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    assistant_settings = config_manager.get_assistant(assistant_id)
    if not assistant_settings:
        raise HTTPException(status_code=404, detail="Assistant not found")

    manifest = plugin_manager.get_plugin_manifest(req.plugin_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Plugin not registered")

    # 防重复
    if any(p.plugin_id == req.plugin_id for p in assistant_settings.plugins):
        raise HTTPException(status_code=400, detail="Plugin already exists on assistant")

    new_plugin = PluginUserConfig(
        plugin_id=req.plugin_id,
        enabled=req.enabled,
        tools_default_enabled=req.tools_default_enabled,
        config=req.config or {},
        tools=[],  # 初始工具启用列表（若模型中表示按工具继承）
    )
    new_list = list(assistant_settings.plugins) + [new_plugin]
    config_manager.update_plugins_for_assistant(assistant_id, new_list)

    running = await assistant_manager.get_all_assistants()
    updated_settings = config_manager.get_assistant(assistant_id)
    return await _build_assistant_admin_detail(updated_settings, running, plugin_manager)


@router.patch("/{assistant_id}/plugins/{plugin_id}", response_model=AssistantAdminDetail)
async def update_plugin_on_assistant(
    assistant_id: str,
    plugin_id: str,
    req: UpdatePluginConfigRequest,
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    config_manager: ConfigManager = Depends(get_config_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    settings = config_manager.get_assistant(assistant_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Assistant not found")

    updated_plugins: list[PluginUserConfig] = []
    found = False
    for p in settings.plugins:
        if p.plugin_id == plugin_id:
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
    return await _build_assistant_admin_detail(updated_settings, running, plugin_manager)


@router.delete("/{assistant_id}/plugins/{plugin_id}", response_model=AssistantAdminDetail)
async def remove_plugin_from_assistant(
    assistant_id: str,
    plugin_id: str,
    config_manager: ConfigManager = Depends(get_config_manager),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
):
    settings = config_manager.get_assistant(assistant_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Assistant not found")

    filtered = [p for p in settings.plugins if p.plugin_id != plugin_id]
    if len(filtered) == len(settings.plugins):
        raise HTTPException(status_code=404, detail="Plugin not found on assistant")

    config_manager.update_plugins_for_assistant(assistant_id, filtered)

    # You might want to await the reload to ensure state is fresh before querying
    await assistant_manager.reload_assistant(assistant_id)

    running = await assistant_manager.get_all_assistants()
    updated_settings = config_manager.get_assistant(assistant_id)
    if not updated_settings:
        raise HTTPException(status_code=404, detail="Assistant disappeared after update")

    return await _build_assistant_admin_detail(updated_settings, running, plugin_manager)
