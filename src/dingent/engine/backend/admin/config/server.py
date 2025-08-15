import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from dingent.engine.backend.assistant import Assistant, get_assistant_manager
from dingent.engine.backend.config_manager import get_config_manager
from dingent.engine.backend.settings import AssistantSettings
from dingent.engine.plugins.manager import PluginManifest, get_plugin_manager
from dingent.engine.plugins.types import PluginUserConfig

router = APIRouter()
config_manager = get_config_manager()
assistant_manager = get_assistant_manager()
plugin_manager = get_plugin_manager()


class ToolAdminDetail(BaseModel):
    name: str
    description: str
    enabled: bool


class PluginAdminDetail(PluginUserConfig):
    # 增加 tools 字段来存放工具的详细信息
    tools: list[ToolAdminDetail] = Field(default_factory=list, description="该插件的工具列表")
    status: str = Field(..., description="运行状态 (e.g., 'active', 'inactive', 'error')")


class AssistantAdminDetail(AssistantSettings):
    status: str = Field(..., description="运行状态 (e.g., 'active', 'inactive', 'error')")
    # plugins 字段的类型应为优化后的 PluginAdminDetail
    plugins: list[PluginAdminDetail] = Field(..., description="该助手的插件配置")


class AppAdminDetail(BaseModel):
    assistants: list[AssistantAdminDetail]


# --- 1. 辅助函数：处理单个插件 ---
async def _build_plugin_admin_detail(plugin_config: PluginManifest, assistant_instance: Assistant | None):
    """根据插件配置和其所属的助手实例，构建带有状态的插件详情。"""

    plugin_instance = None
    tools_details = []

    # 只有当助手实例存在时，才有可能找到插件实例
    if assistant_instance:
        plugin_instance = assistant_instance.plugin_instances.get(plugin_config.name)

    if plugin_instance:
        plugin_status = "active"
        tool_instances = await plugin_instance.list_tools()
        tools_details = [ToolAdminDetail(name=name, description=tool.description, enabled=tool.enabled) for name, tool in tool_instances.items()]
    else:
        plugin_status = "inactive"

    plugin_admin_detail_dict = plugin_config.model_dump()
    plugin_admin_detail_dict.update(status=plugin_status, tools=tools_details)
    return PluginAdminDetail(**plugin_admin_detail_dict)


# --- 2. 辅助函数：处理单个助手 ---
async def _build_assistant_admin_detail(assistant_config: AssistantSettings, running_assistants: dict):
    """根据助手配置和所有正在运行的助手实例，构建带有状态的助手详情。"""

    assistant_instance = running_assistants.get(assistant_config.name)
    assistant_status = "active" if assistant_instance else "inactive"

    # 并发处理该助手下的所有插件
    plugin_tasks = [_build_plugin_admin_detail(p_config, assistant_instance) for p_config in assistant_config.plugins]
    plugin_admin_details = await asyncio.gather(*plugin_tasks)

    assistant_admin_detail_dict = assistant_config.model_dump()

    assistant_admin_detail_dict.update(status=assistant_status, plugins=plugin_admin_details)
    return AssistantAdminDetail(**assistant_admin_detail_dict)


# --- 3. 主路由函数 (现在非常简洁) ---
@router.get("/admin/config/app", response_model=AppAdminDetail)
async def get_app_config_with_status():
    """
    获取完整的应用配置，并为助手和插件注入实时的运行状态。
    """
    app_config = config_manager.get_config()
    running_assistants = await assistant_manager.get_assistants()

    # 并发处理所有助手
    assistant_tasks = [_build_assistant_admin_detail(a_config, running_assistants) for a_config in app_config.assistants]
    assistant_admin_details = await asyncio.gather(*assistant_tasks)

    app_admin_detail_dict = app_config.model_dump(exclude={"assistants"})
    app_admin_detail_dict.update(assistants=assistant_admin_details)
    return AppAdminDetail(**app_admin_detail_dict)


@router.patch("/admin/config/app")
async def update_app_config(config: dict):
    config_manager.update_config(config)


@router.post("admin/assistants")
async def add_assistant(config: dict):
    raise NotImplementedError()
