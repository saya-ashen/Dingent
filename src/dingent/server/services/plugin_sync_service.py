import logging

from sqlmodel import Session, select

from dingent.core.db.models import Plugin
from dingent.core.schemas import PluginManifest
from dingent.core.services.plugin_registry import PluginRegistry  # 你的 Manifest 模型

logger = logging.getLogger(__name__)


import logging
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select

from dingent.core.db.models import Plugin
from dingent.core.schemas import PluginManifest
from dingent.core.services.plugin_registry import PluginRegistry


class PluginSyncService:
    """
    负责将文件系统中的插件状态 (通过 PluginRegistry 获取) 同步到数据库。
    并负责将自定义的配置字段列表转换为标准的 JSON Schema 存储。
    """

    def __init__(self, db_session: Session, registry: PluginRegistry):
        self.db = db_session
        self.registry = registry

    def sync(self) -> None:
        """
        执行完整的同步过程：新增、更新和删除。
        """
        logger.info("Starting database synchronization for plugins...")

        # 1. 获取期望状态 (Filesystem)
        fs_manifests = self.registry.get_all_manifests()
        fs_manifests_map: Dict[str, PluginManifest] = {m.id: m for m in fs_manifests}

        # 2. 获取当前状态 (Database)
        db_plugins = self.db.exec(select(Plugin)).all()
        db_plugins_map: Dict[str, Plugin] = {p.registry_id: p for p in db_plugins}

        # 3. 同步处理
        self._process_upserts(fs_manifests_map, db_plugins_map)
        self._process_deletes(fs_manifests_map, db_plugins_map)

        # 4. 提交事务
        self.db.commit()
        logger.info("Plugin database synchronization complete.")

    # --------------------------------------------------------------------------
    # 核心逻辑流程
    # --------------------------------------------------------------------------

    def _process_upserts(self, fs_map: Dict[str, PluginManifest], db_map: Dict[str, Plugin]):
        """处理新增 (Insert) 和 更新 (Update)"""
        for slug, manifest in fs_map.items():
            db_plugin = db_map.get(slug)

            # 预先计算标准的 JSON Schema，用于后续对比和赋值
            # 假设 manifest.config_schema 是 Pydantic 模型列表
            raw_fields = [c.model_dump() for c in manifest.config_schema] if manifest.config_schema else []
            standard_schema = self._convert_to_json_schema(raw_fields)

            if not db_plugin:
                self._create_plugin(slug, manifest, standard_schema)
            else:
                self._update_plugin_if_needed(db_plugin, manifest, standard_schema)

    def _process_deletes(self, fs_map: Dict[str, PluginManifest], db_map: Dict[str, Plugin]):
        """处理删除 (Delete)"""
        fs_slugs = set(fs_map.keys())
        db_slugs = set(db_map.keys())
        slugs_to_delete = db_slugs - fs_slugs

        for slug in slugs_to_delete:
            self._delete_plugin(db_map[slug])

    # --------------------------------------------------------------------------
    # CRUD 操作细节
    # --------------------------------------------------------------------------

    def _create_plugin(self, slug: str, manifest: PluginManifest, schema: Dict[str, Any]):
        """在数据库中创建新插件"""
        logger.info(f"New plugin found: '{slug}'. Adding to database.")
        new_plugin = Plugin(
            registry_id=slug,
            display_name=manifest.display_name,
            description=manifest.description,
            version=str(manifest.version),
            config_schema=schema,  # 存储转换后的标准 Schema
        )
        self.db.add(new_plugin)

    def _update_plugin_if_needed(self, db_plugin: Plugin, manifest: PluginManifest, new_schema: Dict[str, Any]):
        """检查并更新已存在的插件"""
        updates = {}

        # 检查基础字段变化
        if db_plugin.version != str(manifest.version):
            updates["version"] = str(manifest.version)
        if db_plugin.description != manifest.description:
            updates["description"] = manifest.description
        if db_plugin.display_name != manifest.display_name:
            updates["display_name"] = manifest.display_name

        # [关键] 检查 Schema 是否变化
        # 直接比较字典内容，如果开发者修改了配置定义，这里会触发更新
        if db_plugin.config_schema != new_schema:
            updates["config_schema"] = new_schema

        if updates:
            logger.info(f"Plugin '{db_plugin.registry_id}' has updates ({', '.join(updates.keys())}). Updating DB.")
            for k, v in updates.items():
                setattr(db_plugin, k, v)
            self.db.add(db_plugin)

    def _delete_plugin(self, db_plugin: Plugin):
        """从数据库删除插件"""
        logger.info(f"Plugin '{db_plugin.registry_id}' removed from filesystem. Deleting from database.")
        self.db.delete(db_plugin)

    # --------------------------------------------------------------------------
    # Schema 转换工具 (核心改进)
    # --------------------------------------------------------------------------

    def _convert_to_json_schema(self, custom_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将自定义字段列表转换为标准 JSON Schema 格式。
        """
        if not custom_fields:
            return {}

        # 基础骨架
        json_schema = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,  # 严谨模式：不允许未定义的字段
        }

        # 类型映射表
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "int": "integer",
            "float": "number",
            "number": "number",
            "boolean": "boolean",
            "bool": "boolean",
            "dict": "object",
            "list": "array",
        }

        for field in custom_fields:
            name = field.get("name")
            if not name:
                continue  # 理论上不该发生

            custom_type = field.get("type", "string")
            description = field.get("description", "")
            default_val = field.get("default")
            is_required = field.get("required", False)
            is_secret = field.get("secret", False)  # 虽然JSON Schema没secret，但可以放在扩展字段里给前端用

            # 1. 映射类型
            schema_type = type_mapping.get(custom_type, "string")

            # 2. 构建属性节点
            property_node = {
                "type": schema_type,
                "title": name.replace("_", " ").title(),  # 前端展示友好标题
                "description": description,
            }

            # 3. 处理默认值
            if default_val is not None:
                property_node["default"] = default_val

            # 4. 处理 Secret (可选：虽然不是标准校验字段，但很多前端库支持 ui:widget)
            if is_secret:
                property_node["writeOnly"] = True  # JSON Schema 标准中表示只写（类似密码）
                # 或者使用自定义扩展字段，供前端识别
                property_node["x-ui-secret"] = True

            # 5. 添加到 properties
            json_schema["properties"][name] = property_node

            # 6. 处理 required
            if is_required:
                json_schema["required"].append(name)

        return json_schema
