from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Workflow, WorkflowNode


def find_project_root(marker: str = "dingent.toml") -> Path | None:
    """
    从当前目录开始向上查找项目根目录。
    项目根目录由标记文件 (如 'dingent.toml') 的存在来标识。

    :param marker: 标记文件的名称。
    :return: 项目根目录的Path对象，如果未找到则返回None。
    """
    current_dir = Path.cwd().resolve()

    while current_dir != current_dir.parent:  # 循环直到文件系统的根目录
        if (current_dir / marker).exists():
            return current_dir
        current_dir = current_dir.parent

    # 检查最后一级的根目录 (例如 /)
    if (current_dir / marker).exists():
        return current_dir

    return None


def _ensure_workflow(workflow_or_id: str | Workflow, manager) -> Workflow:
    if isinstance(workflow_or_id, Workflow):
        return workflow_or_id
    wf = manager.get_workflow(workflow_or_id)
    if not wf:
        raise ValueError(f"Workflow '{workflow_or_id}' 不存在")
    return wf


def _build_adjacency(workflow: Workflow) -> dict[str, list[str]]:
    """
    构建从 source node -> [target node ids] 的邻接表。
    只考虑 edge.source -> edge.target（忽略来源的来源，只看目标）。
    """
    adj: dict[str, list[str]] = {}
    for edge in workflow.edges:
        adj.setdefault(edge.source, []).append(edge.target)
    return adj


def get_direct_targets(
    node_id: str,
    workflow_or_id: str | Workflow,
    manager=None,
) -> list[WorkflowNode]:
    """
    获取某节点的直接目标节点（即所有 edge.source == node_id 的 target 节点）。

    Args:
        node_id: 起始节点 ID
        workflow_or_id: Workflow 实例或其 ID
        manager: 可选，指定 WorkflowManager

    Returns:
        目标节点列表（按在 workflow.edges 中出现顺序去重）
    """
    from .workflow_manager import get_workflow_manager

    manager = manager or get_workflow_manager()
    workflow = _ensure_workflow(workflow_or_id, manager)

    targets: list[WorkflowNode] = []
    seen: set[str] = set()
    for edge in workflow.edges:
        if edge.source == node_id:
            if edge.target not in seen:
                node = next((n for n in workflow.nodes if n.id == edge.target), None)
                if node:
                    targets.append(node)
                    seen.add(edge.target)
    return targets


def get_all_targets(
    node_id: str,
    workflow_or_id: str | Workflow,
    manager=None,
    include_start: bool = False,
) -> list[WorkflowNode]:
    """
    递归（图遍历）获取从某节点出发所有可达的目标节点（包含多跳）。

    Args:
        node_id: 起始节点 ID
        workflow_or_id: Workflow 实例或其 ID
        manager: 可选 WorkflowManager
        include_start: 是否在结果中包含起始节点本身

    Returns:
        所有可达目标节点列表（按发现顺序），不包含重复
    """
    from .workflow_manager import get_workflow_manager

    manager = manager or get_workflow_manager()
    workflow = _ensure_workflow(workflow_or_id, manager)
    adjacency = _build_adjacency(workflow)

    # 预构建 id -> node
    node_map = {n.id: n for n in workflow.nodes}
    if node_id not in node_map:
        raise ValueError(f"节点 '{node_id}' 不存在于 workflow '{workflow.id}' 中")

    visited: set[str] = set()
    order: list[WorkflowNode] = []

    dq = deque()
    dq.extend(adjacency.get(node_id, []))

    while dq:
        current = dq.popleft()
        if current in visited:
            continue
        visited.add(current)
        node_obj = node_map.get(current)
        if node_obj:
            order.append(node_obj)
        # 加入当前节点的直接后继
        for nxt in adjacency.get(current, []):
            if nxt not in visited:
                dq.append(nxt)

    if include_start:
        return [node_map[node_id]] + order
    return order


def get_terminal_targets(
    node_id: str,
    workflow_or_id: str | Workflow,
    manager=None,
) -> list[WorkflowNode]:
    """
    获取所有“终端”目标节点：从起始节点可达，且自身没有任何 outgoing edge 的节点。

    Args:
        node_id: 起始节点 ID
        workflow_or_id: Workflow 实例或其 ID
        manager: 可选 WorkflowManager

    Returns:
        终端目标节点列表（顺序依据首次发现顺序）
    """
    from .workflow_manager import get_workflow_manager

    manager = manager or get_workflow_manager()
    workflow = _ensure_workflow(workflow_or_id, manager)
    adjacency = _build_adjacency(workflow)
    node_map = {n.id: n for n in workflow.nodes}
    if node_id not in node_map:
        raise ValueError(f"节点 '{node_id}' 不存在于 workflow '{workflow.id}' 中")

    # 获取所有可达节点
    reachable = get_all_targets(node_id, workflow, manager, include_start=False)
    reachable_ids = {n.id for n in reachable}

    terminal_nodes: list[WorkflowNode] = []
    for n in reachable:
        # 没有后继 或 没有后继在图里（理论上不会）
        if not adjacency.get(n.id):
            terminal_nodes.append(n)
        else:
            # 如果所有后继都不在 reachable_ids 中（异常情况），也视为终端
            nexts = [t for t in adjacency.get(n.id, []) if t in reachable_ids]
            if not nexts:
                terminal_nodes.append(n)
    return terminal_nodes


def describe_targets(
    node_id: str,
    workflow_or_id: str | Workflow,
    manager=None,
) -> dict:
    """
    组合展示接口，方便调试/查看。

    Returns:
        {
          "direct": [ {id, name}, ... ],
          "all": [ {id, name}, ... ],
          "terminal": [ {id, name}, ... ]
        }
    """
    from .workflow_manager import get_workflow_manager

    manager = manager or get_workflow_manager()
    wf = _ensure_workflow(workflow_or_id, manager)

    def pack(nodes: Iterable[WorkflowNode]):
        return [{"id": n.id, "name": n.data.assistantName if getattr(n, "data", None) else n.id} for n in nodes]

    direct = get_direct_targets(node_id, wf, manager)
    all_targets = get_all_targets(node_id, wf, manager, include_start=False)
    terminal = get_terminal_targets(node_id, wf, manager)

    return {
        "workflow_id": wf.id,
        "start_node_id": node_id,
        "direct": pack(direct),
        "all": pack(all_targets),
        "terminal": pack(terminal),
    }
