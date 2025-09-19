import asyncio
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from dingent.core.analytics_manager import AnalyticsManager
from dingent.core.assistant_manager import AssistantManager
from dingent.core.config_manager import ConfigManager
from dingent.core.log_manager import LogManager
from dingent.core.market_service import MarketItemCategory, MarketService
from dingent.core.plugin_manager import PluginManager
from dingent.core.workflow_manager import WorkflowManager
from dingent.server.api.dependencies import (
    get_analytics_manager,
    get_assistant_manager,
    get_config_manager,
    get_log_manager,
    get_market_service,
    get_plugin_manager,
    get_workflow_manager,
)

router = APIRouter(prefix="/overview", tags=["Overview"])


async def _gather_assistants_section(
    config_manager: ConfigManager,
    assistant_manager: AssistantManager,
) -> dict[str, Any]:
    settings_list = config_manager.list_assistants()
    running_instances = await assistant_manager.get_all_assistants(preload=False)

    items = []
    active = 0
    for s in settings_list:
        instance = running_instances.get(s.id)
        status = "active" if instance else "inactive"
        if status == "active":
            active += 1
        enabled_plugins = sum(1 for p in s.plugins if p.enabled)
        items.append(
            {
                "id": s.id,
                "name": s.name,
                "status": status,
                "plugin_count": len(s.plugins),
                "enabled_plugin_count": enabled_plugins,
            }
        )
    return {
        "total": len(settings_list),
        "active": active,
        "inactive": len(settings_list) - active,
        "list": items,
    }


def _gather_plugins_section(plugin_manager: PluginManager) -> dict[str, Any]:
    manifests = plugin_manager.list_plugins()
    items = []
    for pid, manifest in manifests.items():
        tools = []
        try:
            # 尝试静态工具枚举（若插件支持 list_tools 需实例化，这里只统计 manifest 中可见信息）
            # 如果 manifest 没有工具信息，可留空
            tools = getattr(manifest, "tools", []) or []
        except Exception:
            pass
        items.append(
            {
                "id": pid,
                "name": manifest.name,
                "version": manifest.version,
                "tool_count": len(tools),
            }
        )
    return {
        "installed_total": len(manifests),
        "list": items,
    }


def _gather_logs_section(log_manager: LogManager, limit: int = 20) -> dict[str, Any]:
    # recent logs
    try:
        recent = [e.to_dict() for e in log_manager.get_logs(limit=limit)]
    except Exception:
        recent = []
    # stats
    try:
        stats = log_manager.get_log_stats()
    except Exception:
        stats = {}
    return {"recent": recent, "stats": stats}


async def _gather_market_section(
    market_service: MarketService,
    plugin_manager: PluginManager,
) -> dict[str, Any]:
    metadata = None
    plugin_updates = 0
    try:
        metadata_obj = await market_service.get_market_metadata()
        metadata = metadata_obj.model_dump()
    except Exception:
        metadata = None

    try:
        local_versions = plugin_manager.get_installed_versions()  # {plugin_id: version}
        # 获取市场插件项目
        market_plugins = await market_service.get_market_items(MarketItemCategory.plugin, installed_items={"plugins": local_versions})
        for item in market_plugins:
            # 假设 item.id 与 plugin_id 对应, item.version 字段存在
            local_ver = local_versions.get(item.id)
            if local_ver and local_ver != item.version:
                plugin_updates += 1
    except Exception:
        pass

    return {
        "metadata": metadata,
        "plugin_updates": plugin_updates,
    }


def _gather_workflows_section(workflow_manager: WorkflowManager) -> dict[str, Any]:
    workflows = workflow_manager.list_workflows()
    return {
        "total": len(workflows),
        "active_workflow_id": workflow_manager.active_workflow_id,
        "list": [{"id": w.id, "name": w.name} for w in workflows],
    }


def _gather_llm_section(config_manager: ConfigManager) -> dict[str, Any]:
    settings = config_manager.get_settings()
    if settings.llm:
        return settings.llm.model_dump(mode="json")
    return {}


@router.get("")
async def get_overview(
    config_manager: ConfigManager = Depends(get_config_manager),
    assistant_manager: AssistantManager = Depends(get_assistant_manager),
    plugin_manager: PluginManager = Depends(get_plugin_manager),
    log_manager: LogManager = Depends(get_log_manager),
    market_service: MarketService = Depends(get_market_service),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """
    聚合后台核心状态用于 Dashboard 展示的总览接口。
    返回结构示例：
    {
      "assistants": {...},
      "plugins": {...},
      "workflows": {...},
      "logs": {...},
      "market": {...},
      "llm": {...}
    }
    """
    assistants_task = asyncio.create_task(_gather_assistants_section(config_manager, assistant_manager))
    market_task = asyncio.create_task(_gather_market_section(market_service, plugin_manager))

    # 同步部分
    plugins_section = _gather_plugins_section(plugin_manager)
    workflows_section = _gather_workflows_section(workflow_manager)
    logs_section = _gather_logs_section(log_manager)
    llm_section = _gather_llm_section(config_manager)

    assistants_section, market_section = await asyncio.gather(assistants_task, market_task)

    return {
        "assistants": assistants_section,
        "plugins": plugins_section,
        "workflows": workflows_section,
        "logs": logs_section,
        "market": market_section,
        "llm": llm_section,
    }


@router.get("/budget")
async def get_budget(
    # log_manager: LogManager = Depends(get_log_manager),
    analytics_manager: AnalyticsManager = Depends(get_analytics_manager),
):
    budget = analytics_manager.get_user_cost("admin")
    if not budget:
        raise HTTPException(status_code=404, detail="No budget data found")
    return budget
