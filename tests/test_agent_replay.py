from datetime import datetime

from sqlmodel.sql.expression import Select
from dingent.core.llms.service import get_llm_for_context as real_get_llm_for_context
import uuid
import litellm
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session
import os
from fastapi.testclient import TestClient

from dingent.core.db.models import Assistant, AssistantPluginLink, Conversation, Plugin, Workflow, WorkflowEdge, WorkflowNode, Workspace
from tests.utils import create_replay_llm


def mock_full_single_cell_data(workspace_id, session: Session):
    """
    插入完整的 single-cell 模拟数据，包括：
    1. Plugins (Bio Data Loader, Single Cell Analyzer)
    2. Assistants (DataGetter, Analyst)
    3. AssistantPlugin (关联配置)
    4. Workflow & Nodes & Edges
    """

    # ==========================================
    # 1. 预先生成所有需要的 UUID
    # ==========================================
    # Workflow 相关
    wf_id = uuid.uuid4()
    node_start_id = uuid.uuid4()
    node_second_id = uuid.uuid4()

    user_id = uuid.uuid4()  # created_by_id

    # Assistant & Plugin 相关
    plugin_loader_id = uuid.uuid4()  # 对应 bio-data-loader
    plugin_analyzer_id = uuid.uuid4()  # 对应 single-cell-analyzer

    assist_getter_id = uuid.uuid4()  # 对应 DataGetter
    assist_analyst_id = uuid.uuid4()  # 对应 Analyst

    now = datetime.utcnow()

    # ==========================================
    # 2. 创建 Plugins
    # ==========================================
    plugin_loader = Plugin(
        id=plugin_loader_id,
        registry_id="bio-data-loader",
        registry_name="Local",
        display_name="Bio Data Loader",
        description="Bio Data Loader",
        version="1.1.0",
        config_schema={},  # JSON 字段
    )

    plugin_analyzer = Plugin(
        id=plugin_analyzer_id,
        registry_id="Single-Cell-Analyzer",
        registry_name="Local",
        display_name="Single Cell Analyzer",
        description="Single Cell Analyzer",
        version="1.0.0",
        config_schema={},
    )

    # ==========================================
    # 3. 创建 Assistants
    # ==========================================
    # Assistant 1: DataGetter
    assist_getter = Assistant(
        id=assist_getter_id,
        name="DataGetter",
        description="No description",
        version="0.2.0",
        spec_version="2.0",
        enabled=True,
        model_config_id=None,
        created_at=now,
        updated_at=now,
        created_by_id=user_id,
        workspace_id=workspace_id,
        instructions=(
            "You are an expert Data Engineer specializing in Single-Cell Sequencing data preparation. "
            "Your sole objective is to provide a clean, standardized `.h5ad` file path for downstream analysis.\n\n"
            "**Workflow Protocol:**\n\n"
            "1.  **Input Analysis**:\n"
            "    * If the user"
        ),
    )

    # Assistant 2: Analyst
    assist_analyst = Assistant(
        id=assist_analyst_id,
        name="Analyst",
        description=(
            "### 🔬 Single-Cell Analyzer MCP\n\n"
            "A specialized bioinformatics toolkit designed to transform processed single-cell data (.h5ad) "
            "into biological insights and visual reports.\n\n"
            "**Core Capabilities:**\n"
            "* **QC & Filtering**: Automatically filters low-quality cel"
        ),
        version="0.2.0",
        spec_version="2.0",
        enabled=True,
        model_config_id=None,
        created_at=now,
        updated_at=now,
        created_by_id=user_id,
        workspace_id=workspace_id,
        instructions=(
            "You are a Senior Computational Biologist. Your goal is to analyze single-cell data (`.h5ad`) "
            "and generate a scientifically meaningful report.\n\n"
            "**Analysis Pipeline (Execute in Order):**\n\n"
            "1.  **Quality Control (QC)**:\n"
            "    * Run `quality_control_analysis` fi"
        ),
    )

    # ==========================================
    # 4. 创建 AssistantPlugin (关联表)
    # ==========================================
    # 关联: DataGetter -> Bio Data Loader
    ap_getter = AssistantPluginLink(
        assistant_id=assist_getter_id,
        plugin_id=plugin_loader_id,
        enabled=True,
        tool_configs=[],  # JSON List
    )

    # 关联: Analyst -> Single Cell Analyzer
    ap_analyst = AssistantPluginLink(
        assistant_id=assist_analyst_id,
        plugin_id=plugin_analyzer_id,
        enabled=True,
        tool_configs=[],
    )

    # ==========================================
    # 5. 创建 Workflow & Nodes (引用上面的 Assistant ID)
    # ==========================================
    workflow = Workflow(
        id=wf_id,
        name="single-cell",
        created_at=now,
        updated_at=now,
        workspace_id=workspace_id,
        created_by_id=user_id,
    )

    # Node 1: 使用 DataGetter (Start Node)
    node_start = WorkflowNode(
        id=node_start_id,
        workflow_id=wf_id,
        assistant_id=assist_getter_id,  # <--- 引用 DataGetter
        type="assistant",
        is_start_node=True,
        position={"x": 62.33331298828125, "y": 266.3333282470703},
        measured={"width": 100.0, "height": 80.0},
    )

    # Node 2: 使用 Analyst
    node_second = WorkflowNode(
        id=node_second_id,
        workflow_id=wf_id,
        assistant_id=assist_analyst_id,  # <--- 引用 Analyst
        type="assistant",
        is_start_node=False,
        position={"x": 254.99996948242188, "y": 290.99999237060547},
        measured={"width": 100.0, "height": 80.0},
    )

    edge = WorkflowEdge(
        id=uuid.uuid4(),
        workflow_id=wf_id,
        source_node_id=node_start_id,
        target_node_id=node_second_id,
        source_handle="right-out",
        target_handle="left-in",
        type="directional",
        mode="single",
    )

    # ==========================================
    # 6. 提交到数据库
    # ==========================================
    # 添加 Plugins
    session.add(plugin_loader)
    session.add(plugin_analyzer)

    # 添加 Assistants
    session.add(assist_getter)
    session.add(assist_analyst)

    # 添加 AssistantPlugins (如果这是中间表对象)
    # 注意：如果你的 Assistant 模型有关联属性 (e.g. assistant.plugins.append)，也可以用那种方式。
    # 这里假设是手动操作中间表对象：
    session.add(ap_getter)
    session.add(ap_analyst)

    # 添加 Workflow
    session.add(workflow)
    session.add(node_start)
    session.add(node_second)
    session.add(edge)

    session.commit()

    return {
        "workflow": workflow,
        "assistants": {"getter": assist_getter, "analyst": assist_analyst},
        "nodes": [node_start, node_second],
    }


def test_run_agent_endpoint_with_replay(
    client: TestClient,
    session: Session,
    create_workspace,
):
    """
    测试 /chat/agent/{id}/run 接口，使用回放数据模拟 LLM 返回
    """

    # ---------------------------------------------------------
    # 1. 准备数据库数据 (必不可少，否则接口报 404/403)
    # ---------------------------------------------------------

    ws: Workspace = create_workspace()
    data = mock_full_single_cell_data(ws.id, session)
    # wf: Workflow = data["workflow"]
    wf = session.get(Workflow, data["workflow"].id)

    assert wf and wf.name == "single-cell"

    # ---------------------------------------------------------
    # 2. 准备 Mock LLM
    # ---------------------------------------------------------
    # 加载我们之前导出的 MLflow 数据
    import os

    data_path = os.path.join(os.path.dirname(__file__), "data/trace.json")
    mock_llm_instance = create_replay_llm(data_path)

    def get_llm_wrapper(*args, **kwargs):
        # A. 先调用原始逻辑，获取完全初始化的真实对象
        # 这样你就保留了 LangChain/SDK 的所有功能（bind_tools, callbacks 等）
        real_llm_instance = real_get_llm_for_context(*args, **kwargs)

        # B. 针对性地修改这个对象的 client 属性
        # 你的报错代码是: return await self.client.acompletion(**kwargs)
        # 所以我们只需要把 self.client.acompletion 换成我们的 mock

        if hasattr(real_llm_instance, "client"):
            # 注意：这里直接赋值，Python 允许动态修改实例属性
            # 无论 client 是 litellm 模块还是 Router 对象，这里都会生效

            # 1. 替换异步方法 (关键)
            real_llm_instance.client.acompletion = mock_replay.acompletion

            # 2. 替换同步方法 (为了保险)
            real_llm_instance.client.completion = mock_replay.completion

            print("DEBUG: Successfully patched LLM client inside wrapper")
        else:
            print(f"WARNING: llm_instance has no 'client' attribute. Type: {type(real_llm_instance)}")

        return real_llm_instance

    # ---------------------------------------------------------
    # 3. 构造请求参数
    # ---------------------------------------------------------
    thread_id = str(uuid.uuid4())
    input_payload = {
        "thread_id": thread_id,
        "input": "Analyze the data",  # RunAgentInput 的字段
        "messages": [{"role": "user", "content": "Analyze the data"}],
    }
    input_payload = {
        "threadId": "2755cd2f-4329-44df-b22d-61621775fce5",
        "runId": "f26e1be5-1ce9-423b-9d2d-652c472369ff",
        "tools": [],
        "context": [],
        "forwardedProps": {
            "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjoxNzcwODIwNTE0fQ.TyN5PNsVyfSlQYcs9Z1-Mloqdm99b4Cldp2Wl6UldCY",
            "workspace_slug": "user-9bb06de9-0fb9-4264-93b3-ddaae11144a2-workspace",
            "is_guest": False,
        },
        "state": {},
        "messages": [
            {
                "id": "522fa5a4-1586-4965-8447-dfb319ca527e",
                "role": "user",
                "content": "加载 paul15 造血干细胞数据集。除了基础的聚类外，我特别想看细胞的分化轨迹。请运行 PAGA 分析，并在报告中展示细胞是如何从干细胞分化成不同祖细胞的。",
            }
        ],
    }

    # 伪造 Headers (模拟你是这个 Workspace 下的访客)
    # 注意：你的依赖 CurrentWorkspaceAllowGuest 可能会根据 header 或 cookie 解析
    # 这里假设它通过 X-Workspace-ID 或域名解析，请根据实际逻辑调整
    headers = {
        "X-Visitor-ID": "test-visitor-001",
        "X-Workspace-ID": str(wf.id),
    }

    # ---------------------------------------------------------
    # 4. 执行测试：Patch + Client.post
    # ---------------------------------------------------------

    # 拦截 litellm.completion，让它吐出 Mock 数据
    os.environ["OPENAI_API_KEY"] = "MOCK_KEY"
    target_path = "dingent.core.llms.service.get_llm_for_context"
    with patch(target_path) as mock_get_llm:
        mock_get_llm.return_value = mock_llm_instance
        response = client.post(
            f"/api/v1/{ws.slug}/chat/agent/{wf.name}/run",
            json=input_payload,
            headers=headers,
        )

        # ---------------------------------------------------------
        # 5. 验证结果
        # ---------------------------------------------------------

        # A. 验证 HTTP 状态码
        assert response.status_code == 200, f"Error: {response.text}"

        # B. 验证流式输出
        # 因为是 StreamingResponse，我们需要读取内容
        content = response.content.decode("utf-8")
        assert len(content) > 0

        # 验证返回的内容里确实包含了我们的 Mock 数据
        # 假设 Mock 数据里有一句 "Senior Computational Biologist"
        assert "Senior Computational Biologist" in content

        # C. 验证数据库副作用 (Conversation 是否被更新)
        session.expire_all()  # 强制从数据库重读
        saved_conversation = session.exec(Select(Conversation)).first()

        assert saved_conversation is not None
