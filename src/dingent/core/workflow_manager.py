from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING

from loguru import logger
from pydantic import ValidationError

from dingent.core.config_manager import ConfigManager
from dingent.core.log_manager import log_with_context
from dingent.core.settings import AppSettings
from dingent.core.types import (
    Workflow,
    WorkflowCreate,
    WorkflowUpdate,
)

if TYPE_CHECKING:
    # Adapt these imports to your actual project structure
    from dingent.core.assistant_manager import AssistantManager

    from .assistant_manager import Assistant  # runtime Assistant instance (if different path adjust)


# ---------------------------------------------------------------------------
# Design Notes
# ---------------------------------------------------------------------------
# 1. ConfigManager (新版本) 不再持久化 workflows 列表；WorkflowManager 完全接管
#    workflows 的文件读取、校验、写入、删除。
# 2. ConfigManager 只需要维护 current_workflow (id)。当 active workflow 改变时，
#    WorkflowManager 会调用 config_manager.update_global({"current_workflow": id})
# 3. Workflow 文件存储位置：{project_root}/config/workflows/{workflow_id}.json
# 4. Runtime 相关逻辑（instantiate_workflow_assistants）仍然保留，但建议未来拆分到
#    WorkflowRuntimeOrchestrator / GraphBuilder，以避免 Manager 过胖。
# 5. 提供订阅机制 (on_change) 用于通知外部（如 UI / 监控）Workflow 的 CRUD 与 active 变化。
# 6. 提供原子写入、防止并发冲突 (RLock)。
# 7. 提供图导出 (build_adjacency) 便于调试或可视化。
# 8. 提供批量导入/导出 snapshot。
#
# 可进一步增强（暂未实现）：
# - 文件变更监听 (watchdog) -> 自动 reload
# - 版本迁移（如 Workflow schema 升级）
# - 校验拓扑循环、孤立节点等
# ---------------------------------------------------------------------------


WorkflowChangeCallback = Callable[[str, str, Workflow | None], None]
# event types: "created", "updated", "deleted", "activated", "deactivated", "reloaded"


class WorkflowManager:
    """
    Manages workflow persistence (CRUD) + active workflow selection + (optional) runtime assistant instantiation.

    Responsibilities:
      - Load all workflow JSON definitions from config/workflows
      - CRUD operations on workflows
      - Track / persist current active workflow id via ConfigManager
      - Provide runtime assistant instantiation helper (optional)
      - Emit change events to registered callbacks for observability
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        assistant_manager: AssistantManager | None = None,
        workflows_dir: Path | None = None,
        auto_set_active_if_missing: bool = True,
    ):
        self.config_manager = config_manager
        self.assistant_manager = assistant_manager  # may be None if only doing CRUD
        self._dir = workflows_dir or (config_manager.project_root / "config" / "workflows")
        self._lock = RLock()

        self._workflows: dict[str, Workflow] = {}
        self._active_workflow_id: str | None = None
        self._callbacks: list[WorkflowChangeCallback] = []

        self._load_all_from_disk()

        # Sync active workflow from config
        settings = self.config_manager.get_settings()
        if settings.current_workflow and settings.current_workflow in self._workflows:
            self._active_workflow_id = settings.current_workflow
        elif auto_set_active_if_missing and self._workflows:
            first_id = next(iter(self._workflows.keys()))
            self._active_workflow_id = first_id
            self._persist_active_workflow_id(first_id)

        # Register callback to handle assistant deletions
        self.config_manager.register_on_change(self._on_config_change)

        logger.info(
            "WorkflowManager initialized",
            extra={
                "count": len(self._workflows),
                "active": self._active_workflow_id,
                "dir": str(self._dir),
            },
        )

    # -----------------------------------------------------------------------
    # Public Query APIs
    # -----------------------------------------------------------------------
    def list_workflows(self) -> list[Workflow]:
        with self._lock:
            return [wf.model_copy(deep=True) for wf in self._workflows.values()]

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        with self._lock:
            wf = self._workflows.get(workflow_id)
            return wf.model_copy(deep=True) if wf else None

    def get_workflow_id_by_name(self, name: str) -> str | None:
        with self._lock:
            for wf in self._workflows.values():
                if wf.name == name:
                    return wf.id
            return None

    @property
    def active_workflow_id(self) -> str | None:
        with self._lock:
            return self._active_workflow_id

    def is_active(self, workflow_id: str) -> bool:
        with self._lock:
            return self._active_workflow_id == workflow_id

    # -----------------------------------------------------------------------
    # CRUD
    # -----------------------------------------------------------------------
    def create_workflow(self, wf_create: WorkflowCreate, *, make_active: bool = False, forbid_duplicate_name: bool = True) -> Workflow:
        with self._lock:
            if forbid_duplicate_name and any(wf.name == wf_create.name for wf in self._workflows.values()):
                raise ValueError(f"Workflow name '{wf_create.name}' already exists.")

            workflow_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            wf = Workflow(
                id=workflow_id,
                name=wf_create.name,
                description=wf_create.description,
                nodes=[],
                edges=[],
                created_at=now,
                updated_at=now,
            )
            self._workflows[workflow_id] = wf
            self._write_workflow_file(wf)
            if make_active:
                self._set_active_locked(workflow_id)
            self._emit_change("created", workflow_id, wf)
            return wf.model_copy(deep=True)

    def update_workflow(self, workflow_id: str, wf_update: WorkflowUpdate) -> Workflow:
        with self._lock:
            existing = self._workflows.get(workflow_id)
            if not existing:
                raise ValueError(f"Workflow '{workflow_id}' not found.")

            patch = wf_update.model_dump(exclude_unset=True)
            if not patch:
                return existing.model_copy(deep=True)

            # Prevent name collisions
            if "name" in patch:
                for wid, wf in self._workflows.items():
                    if wid != workflow_id and wf.name == patch["name"]:
                        raise ValueError(f"Another workflow already uses name '{patch['name']}'.")

            updated = existing.model_copy(update=patch)
            updated.updated_at = datetime.utcnow().isoformat()

            # Validate by re-parsing (ensures nodes/edges still pass model validation)
            try:
                updated = Workflow.model_validate(updated.model_dump())
            except ValidationError as e:
                raise ValueError(f"Invalid workflow update: {e}") from e

            self._workflows[workflow_id] = updated
            self._write_workflow_file(updated)
            self._emit_change("updated", workflow_id, updated)
            return updated.model_copy(deep=True)

    def save_workflow(self, workflow: Workflow) -> Workflow:
        """
        Full replace save. Use update_workflow for partial patch.
        """
        with self._lock:
            if workflow.id not in self._workflows:
                raise ValueError(f"Cannot save unknown workflow '{workflow.id}'.")
            workflow.updated_at = datetime.now(UTC).isoformat()
            # Validate
            wf_valid = Workflow.model_validate(workflow.model_dump())
            self._workflows[wf_valid.id] = wf_valid
            self._write_workflow_file(wf_valid)
            self._emit_change("updated", wf_valid.id, wf_valid)
            return wf_valid.model_copy(deep=True)

    def delete_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            if workflow_id not in self._workflows:
                return False
            wf = self._workflows.pop(workflow_id)
            self._delete_workflow_file(workflow_id)
            if self._active_workflow_id == workflow_id:
                self._active_workflow_id = None
                self._persist_active_workflow_id(None)
                self._emit_change("deactivated", workflow_id, None)
            self._emit_change("deleted", workflow_id, wf)
            return True

    def rename_workflow(self, workflow_id: str, new_name: str) -> Workflow:
        return self.update_workflow(workflow_id, WorkflowUpdate(name=new_name))

    def cleanup_workflows_for_deleted_assistant(self, assistant_id: str) -> list[str]:
        """
        Clean up all workflows by removing nodes that reference the deleted assistant
        and their connected edges. Returns list of workflow IDs that were modified.
        """
        modified_workflow_ids = []

        with self._lock:
            for workflow_id, workflow in self._workflows.items():
                # Find nodes that reference the deleted assistant
                nodes_to_remove = [node for node in workflow.nodes if node.data.assistantId == assistant_id]

                if not nodes_to_remove:
                    continue  # No changes needed for this workflow

                # Get IDs of nodes to remove
                node_ids_to_remove = {node.id for node in nodes_to_remove}

                # Remove nodes that reference the deleted assistant
                updated_nodes = [node for node in workflow.nodes if node.data.assistantId != assistant_id]

                # Remove edges that connect to/from the removed nodes
                updated_edges = [edge for edge in workflow.edges if edge.source not in node_ids_to_remove and edge.target not in node_ids_to_remove]

                # Update the workflow
                workflow.nodes = updated_nodes
                workflow.edges = updated_edges
                workflow.updated_at = datetime.utcnow().isoformat()

                # Persist changes
                self._write_workflow_file(workflow)
                self._emit_change("updated", workflow_id, workflow)
                modified_workflow_ids.append(workflow_id)

        return modified_workflow_ids

    def _on_config_change(self, old_settings: AppSettings, new_settings: AppSettings) -> None:
        """Handle configuration changes, specifically assistant deletions."""
        try:
            # Get list of assistant IDs before and after the change
            old_assistant_ids = {assistant.id for assistant in old_settings.assistants}
            new_assistant_ids = {assistant.id for assistant in new_settings.assistants}

            # Find deleted assistants
            deleted_assistant_ids = old_assistant_ids - new_assistant_ids

            # Clean up workflows for each deleted assistant
            for assistant_id in deleted_assistant_ids:
                modified_workflows = self.cleanup_workflows_for_deleted_assistant(assistant_id)
                if modified_workflows:
                    logger.info(f"Cleaned up workflows {modified_workflows} after assistant {assistant_id} deletion")

        except Exception as e:
            logger.error(f"Error handling config change for workflow cleanup: {e}")

    # -----------------------------------------------------------------------
    # Active Workflow
    # -----------------------------------------------------------------------
    def set_active(self, workflow_id: str) -> None:
        with self._lock:
            self._set_active_locked(workflow_id)

    def clear_active(self) -> None:
        with self._lock:
            if self._active_workflow_id is not None:
                old_id = self._active_workflow_id
                self._active_workflow_id = None
                self._persist_active_workflow_id(None)
                self._emit_change("deactivated", old_id, None)

    def _set_active_locked(self, workflow_id: str) -> None:
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow '{workflow_id}' not found.")
        if self._active_workflow_id == workflow_id:
            return
        self._active_workflow_id = workflow_id
        self._persist_active_workflow_id(workflow_id)
        self._emit_change("activated", workflow_id, self._workflows[workflow_id])

    def _persist_active_workflow_id(self, workflow_id: str | None) -> None:
        try:
            self.config_manager.update_global({"current_workflow": workflow_id})
        except Exception as e:
            logger.error(f"Failed to persist current_workflow in ConfigManager: {e}")

    # -----------------------------------------------------------------------
    # Bulk / Snapshot
    # -----------------------------------------------------------------------
    def export_snapshot(self) -> dict:
        with self._lock:
            return {
                "active_workflow_id": self._active_workflow_id,
                "workflows": [wf.model_dump() for wf in self._workflows.values()],
            }

    def import_snapshot(self, snapshot: dict, *, overwrite: bool = True, make_active_if_present: bool = True) -> None:
        """
        snapshot format:
        {
          "active_workflow_id": "...",
          "workflows": [ {workflow_dict} ... ]
        }
        """
        with self._lock:
            wfs_data = snapshot.get("workflows", [])
            loaded: dict[str, Workflow] = {}
            for entry in wfs_data:
                try:
                    wf = Workflow.model_validate(entry)
                    loaded[wf.id] = wf
                except ValidationError as e:
                    logger.error(f"Skip invalid workflow in snapshot: {e}")

            if overwrite:
                # clear all existing
                self._workflows.clear()
                # optionally clean directory
                self._dir.mkdir(parents=True, exist_ok=True)
                for f in self._dir.glob("*.json"):
                    try:
                        f.unlink()
                    except Exception:
                        pass

            # Merge (overwrite existing ids)
            self._workflows.update(loaded)

            # Persist all
            for wf in loaded.values():
                self._write_workflow_file(wf)

            if make_active_if_present:
                active_id = snapshot.get("active_workflow_id")
                if active_id and active_id in self._workflows:
                    self._set_active_locked(active_id)
                elif not self._active_workflow_id and self._workflows:
                    # fallback
                    self._set_active_locked(next(iter(self._workflows.keys())))

            self._emit_change("reloaded", "*", None)

    # -----------------------------------------------------------------------
    # Reload (disk -> memory)
    # -----------------------------------------------------------------------
    def reload_from_disk(self) -> None:
        with self._lock:
            self._load_all_from_disk()
            # Ensure active still valid
            if self._active_workflow_id and self._active_workflow_id not in self._workflows:
                old_id = self._active_workflow_id
                self._active_workflow_id = None
                self._persist_active_workflow_id(None)
                self._emit_change("deactivated", old_id, None)
            self._emit_change("reloaded", "*", None)

    # -----------------------------------------------------------------------
    # Graph Utilities
    # -----------------------------------------------------------------------
    def build_adjacency(
        self,
        workflow_id: str,
        *,
        include_self_loops: bool = False,
        honor_bidirectional: bool = True,
    ) -> dict[str, list[str]]:
        """
        Returns: assistantName -> sorted list of destination assistantNames
        """
        with self._lock:
            wf = self._workflows.get(workflow_id)
            if not wf:
                raise ValueError(f"Workflow '{workflow_id}' not found.")

            node_id_to_assistant: dict[str, str] = {}
            for node in wf.nodes:
                node_id_to_assistant[node.id] = node.data.assistantName

            adjacency: dict[str, set] = {aname: set() for aname in node_id_to_assistant.values()}

            for edge in wf.edges:
                src_a = node_id_to_assistant.get(edge.source)
                tgt_a = node_id_to_assistant.get(edge.target)
                if not src_a or not tgt_a:
                    continue

                if include_self_loops or src_a != tgt_a:
                    adjacency.setdefault(src_a, set()).add(tgt_a)

                if honor_bidirectional and getattr(edge, "data", None):
                    mode = getattr(edge.data, "mode", None)
                    if mode == "bidirectional":
                        if include_self_loops or tgt_a != src_a:
                            adjacency.setdefault(tgt_a, set()).add(src_a)

            return {k: sorted(v) for k, v in adjacency.items()}

    # -----------------------------------------------------------------------
    # Runtime Assistant Instantiation
    # -----------------------------------------------------------------------
    async def instantiate_workflow_assistants(
        self,
        workflow_id: str,
        *,
        set_active: bool = True,
        reset_assistants: bool = True,
        include_self_loops: bool = False,
        honor_bidirectional: bool = True,
        mutate_assistant_destinations: bool = True,
    ) -> dict[str, Assistant]:
        """
        Construct runtime assistant instances according to the workflow graph.

        Args:
          workflow_id: target workflow
          set_active: mark as active workflow
          reset_assistants: if True, calls assistant_manager.aclose() before building
          include_self_loops: keep A->A edges
          honor_bidirectional: expand bidirectional edges
          mutate_assistant_destinations: if True, assigns computed destinations to assistant.destinations
        """
        if not self.assistant_manager:
            raise RuntimeError("assistant_manager is not attached to WorkflowManager.")

        wf = self.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        adj = self.build_adjacency(
            workflow_id,
            include_self_loops=include_self_loops,
            honor_bidirectional=honor_bidirectional,
        )

        if reset_assistants:
            await self.assistant_manager.aclose()

        # Build mapping assistantName -> assistantId from workflow nodes
        assistant_name_to_id: dict[str, str] = {}
        for node in wf.nodes:
            assistant_name_to_id[node.data.assistantName] = node.data.assistantId

        result: dict[str, Assistant] = {}
        for aname, aid in assistant_name_to_id.items():
            try:
                assistant = await self.assistant_manager.get_assistant(aid)
            except ValueError as e:
                log_with_context(
                    "error",
                    message="Failed to instantiate assistant for workflow: {assistant_id}",
                    context={"assistant_id": aid, "assistant_name": aname, "error": str(e)},
                )
                continue
            if mutate_assistant_destinations:
                assistant.destinations = adj.get(aname, [])
            result[aname] = assistant

        if set_active:
            self.set_active(workflow_id)

        return result

    # -----------------------------------------------------------------------
    # Change Event Subscription
    # -----------------------------------------------------------------------
    def register_callback(self, cb: WorkflowChangeCallback) -> None:
        with self._lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def unregister_callback(self, cb: WorkflowChangeCallback) -> None:
        with self._lock:
            if cb in self._callbacks:
                self._callbacks.remove(cb)

    # -----------------------------------------------------------------------
    # Internal: Disk I/O
    # -----------------------------------------------------------------------
    def _load_all_from_disk(self) -> None:
        self._workflows.clear()
        if not self._dir.exists():
            return
        for file in self._dir.glob("*.json"):
            try:
                wf = self._load_single_file(file)
                if wf:
                    self._workflows[wf.id] = wf
            except Exception as e:
                logger.error(f"Failed loading workflow file {file}: {e}")

    def _load_single_file(self, path: Path) -> Workflow | None:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        try:
            wf = Workflow.model_validate(raw)
            return wf
        except ValidationError as e:
            logger.error(f"Workflow file {path} invalid: {e}")
            return None

    def _write_workflow_file(self, wf: Workflow) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{wf.id}.json"
        tmp_path = path.with_suffix(".json.tmp")
        data = wf.model_dump()
        try:
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(path)
        except Exception as e:
            logger.error(f"Failed to write workflow file {path}: {e}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            raise

    def _delete_workflow_file(self, workflow_id: str) -> None:
        path = self._dir / f"{workflow_id}.json"
        if path.exists():
            try:
                path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete workflow file {workflow_id}: {e}")

    # -----------------------------------------------------------------------
    # Internal: Events
    # -----------------------------------------------------------------------
    def _emit_change(self, event: str, workflow_id: str, wf: Workflow | None) -> None:
        for cb in list(self._callbacks):
            try:
                cb(event, workflow_id, wf)
            except Exception as e:
                logger.error(f"Workflow change callback error: {e}")
