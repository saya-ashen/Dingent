from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from dingent.core.types import Workflow, WorkflowCreate, WorkflowUpdate  # 依据你的真实路径
from dingent.core.utils import find_project_root

# 引入 AssistantManager

if TYPE_CHECKING:
    from .assistant_manager import Assistant


class WorkflowManager:
    """Manages workflow configurations and storage, and can instantiate runtime assistants for a workflow."""

    def __init__(self, config_dir: Path | None = None):
        self.project_root = find_project_root()
        assert self.project_root
        self.config_dir = config_dir or self.project_root / "config" / "workflows"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._workflows: dict[str, Workflow] = {}
        self._active_workflow_id: str | None = None  # 当前运行中的 workflow（可选）
        self._load_workflows()

    # -------------------- Persistence --------------------

    def _get_workflow_file_path(self, workflow_id: str) -> Path:
        return self.config_dir / f"{workflow_id}.json"

    def _load_workflows(self) -> None:
        self._workflows.clear()
        if not self.config_dir.exists():
            return
        for file_path in self.config_dir.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    workflow_data = json.load(f)
                    workflow = Workflow(**workflow_data)
                    self._workflows[workflow.id] = workflow
            except Exception as e:
                print(f"Warning: Failed to load workflow from {file_path}: {e}")

    def _save_workflow_to_file(self, workflow: Workflow) -> None:
        file_path = self._get_workflow_file_path(workflow.id)
        workflow_dict = workflow.model_dump()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(workflow_dict, f, indent=2, ensure_ascii=False)

    def _delete_workflow_file(self, workflow_id: str) -> None:
        file_path = self._get_workflow_file_path(workflow_id)
        if file_path.exists():
            file_path.unlink()

    # -------------------- CRUD API --------------------

    def get_workflows(self) -> list[Workflow]:
        return list(self._workflows.values())

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def get_workflow_id_by_name(self, name: str) -> str | None:
        wf = next((wf for wf in self._workflows.values() if wf.name == name), None)
        return wf.id if wf else None

    def create_workflow(self, workflow_create: WorkflowCreate) -> Workflow:
        workflow_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        workflow = Workflow(
            id=workflow_id,
            name=workflow_create.name,
            description=workflow_create.description,
            nodes=[],
            edges=[],
            created_at=now,
            updated_at=now,
        )
        self._workflows[workflow_id] = workflow
        self._save_workflow_to_file(workflow)
        return workflow

    def update_workflow(self, workflow_id: str, workflow_update: WorkflowUpdate) -> Workflow | None:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        update_data = workflow_update.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.now().isoformat()
            for field, value in update_data.items():
                setattr(workflow, field, value)
            self._save_workflow_to_file(workflow)
        return workflow

    def save_workflow(self, workflow: Workflow) -> Workflow:
        workflow.updated_at = datetime.now().isoformat()
        self._workflows[workflow.id] = workflow
        self._save_workflow_to_file(workflow)
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id not in self._workflows:
            return False
        del self._workflows[workflow_id]
        self._delete_workflow_file(workflow_id)
        if self._active_workflow_id == workflow_id:
            self._active_workflow_id = None
        return True

    def reload_workflows(self) -> None:
        self._load_workflows()

    # -------------------- Runtime Assistant Instantiation --------------------

    async def instantiate_workflow_assistants(
        self,
        workflow_id: str,
        *,
        set_active: bool = True,
        reset_assistants: bool = True,
        include_self_loops: bool = False,
        honor_bidirectional: bool = True,
    ) -> dict[str, Assistant]:
        """
        根据指定 workflow 计算并构建（或重用）所有需要的 Assistants，并为每个 Assistant 填写 destinations。

        适用于“只有一个运行中的 workflow”场景：
          - 可以安全地把 destinations 直接存到 Assistant.destinations。
          - 若切换 workflow，可选 reset_assistants=True 来清空旧实例避免状态残留。

        Args:
          workflow_id: 要实例化的 workflow ID
          set_active: 是否将其标记为当前活动 workflow
          reset_assistants: 为 True 时会先关闭并清空现有 Assistant 实例缓存
          include_self_loops: 若为 True，允许 A -> A 自环；否则忽略自环
          honor_bidirectional: 若为 True，edge.data.mode == 'bidirectional' 时加入反向链接

        Returns:
          dict[str, Assistant]: assistant_name -> Assistant 实例（包含已设置的 destinations）
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        from .assistant_manager import get_assistant_manager

        assistant_manager = get_assistant_manager()

        if reset_assistants:
            await assistant_manager.aclose()

        # 1. 收集所有节点涉及的 assistantName
        node_to_assistant: dict[str, str] = {}
        assistant_pairs: dict[str, str] = {}
        for node in workflow.nodes:
            data = node.data
            aname = data.assistantName
            node_to_assistant[node.id] = aname
            assistant_pairs[aname] = data.assistantId  # 记录 name -> id 映射

        # 2. 构建 assistant -> destinations 映射
        dest_map: dict[str, set[str]] = {aname: set() for aname in assistant_pairs.keys()}

        for edge in workflow.edges:
            src_aname = node_to_assistant.get(edge.source)
            tgt_aname = node_to_assistant.get(edge.target)
            if not src_aname or not tgt_aname:
                continue

            # 正向
            if include_self_loops or src_aname != tgt_aname:
                dest_map[src_aname].add(tgt_aname)

            # 处理双向（bidirectional）
            if honor_bidirectional and getattr(edge, "data", None):
                mode = getattr(edge.data, "mode", None)
                if mode == "bidirectional":
                    if include_self_loops or src_aname != tgt_aname:
                        dest_map[tgt_aname].add(src_aname)

        # 3. 创建/获取 Assistant 实例
        result: dict[str, Assistant] = {}
        for aname, aid in assistant_pairs.items():
            assistant = await assistant_manager.get_assistant(aid)
            # 4. 写入 destinations（排序保证稳定性）
            assistant.destinations = sorted(dest_map.get(aname, set()))
            result[aname] = assistant

        if set_active:
            self._active_workflow_id = workflow_id

        return result

    @property
    def active_workflow_id(self) -> str | None:
        return self._active_workflow_id

    def clear_active_workflow(self):
        self._active_workflow_id = None


# Global workflow manager instance
_workflow_manager: WorkflowManager | None = None


def get_workflow_manager() -> WorkflowManager:
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager
