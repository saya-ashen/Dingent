# in a new file, e.g., my_app/plugins/sync_service.py

import logging
from typing import List, Dict
from sqlmodel import Session, select

from dingent.core.db.models import Plugin
from dingent.core.schemas import PluginManifest
from dingent.core.services.plugin_registry import PluginRegistry  # 你的 Manifest 模型

logger = logging.getLogger(__name__)


class PluginSyncService:
    """
    负责将文件系统中的插件状态 (通过 PluginRegistry 获取) 同步到数据库。
    """

    def __init__(self, db_session: Session, registry: PluginRegistry):
        self.db = db_session
        self.registry = registry

    def sync(self) -> None:
        """
        执行完整的同步过程：新增、更新和删除。
        """
        logger.info("Starting database synchronization for plugins...")

        # 1. 从文件系统获取“期望状态”
        fs_manifests = self.registry.get_all_manifests()
        fs_manifests_map: Dict[str, PluginManifest] = {
            # 假设 manifest.id 就是 plugin_slug
            m.id: m
            for m in fs_manifests
        }

        # 2. 从数据库获取“当前持久化状态”
        statement = select(Plugin)
        db_plugins = self.db.exec(statement).all()
        db_plugins_map: Dict[str, Plugin] = {p.plugin_slug: p for p in db_plugins}

        # 3. 计算差异并执行操作

        # --- 处理新增和更新 ---
        for slug, manifest in fs_manifests_map.items():
            db_plugin = db_plugins_map.get(slug)

            if not db_plugin:
                # 数据库中不存在 -> 新增
                logger.info(f"New plugin found: '{slug}'. Adding to database.")
                manifest.config_schema
                config_schema = [c.model_dump() for c in manifest.config_schema] if manifest.config_schema else []
                new_plugin = Plugin(
                    plugin_slug=slug,
                    display_name=manifest.display_name,
                    description=manifest.description,
                    version=str(manifest.version),
                    config_schema=config_schema,
                )
                self.db.add(new_plugin)
            else:
                # 数据库中已存在 -> 检查是否需要更新
                if db_plugin.version != manifest.version or db_plugin.description != manifest.description or db_plugin.display_name != manifest.display_name:
                    logger.info(f"Plugin '{slug}' has updates. Updating database record.")
                    db_plugin.version = str(manifest.version)
                    db_plugin.description = manifest.description
                    db_plugin.display_name = manifest.display_name
                    self.db.add(db_plugin)  # 在 session 中标记为待更新

        # --- 处理删除 ---
        fs_slugs = set(fs_manifests_map.keys())
        db_slugs = set(db_plugins_map.keys())
        slugs_to_delete = db_slugs - fs_slugs

        if slugs_to_delete:
            for slug in slugs_to_delete:
                logger.info(f"Plugin '{slug}' removed from filesystem. Deleting from database.")
                plugin_to_delete = db_plugins_map[slug]
                self.db.delete(plugin_to_delete)

        # 4. 提交事务
        self.db.commit()
        logger.info("Plugin database synchronization complete.")
