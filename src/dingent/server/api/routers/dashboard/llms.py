import time
from uuid import UUID

import litellm
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from dingent.core.db.models import LLMModelConfig, User, Workspace
from dingent.server.api.dependencies import get_current_user, get_current_workspace, get_db_session
from dingent.server.api.schemas import LLMModelConfigCreate, LLMModelConfigRead, LLMModelConfigUpdate, TestConnectionRequest, TestConnectionResponse

router = APIRouter(prefix="/llms", tags=["LLMs"])


@router.get("/", response_model=list[LLMModelConfigRead])
async def list_models(
    workspace: Workspace = Depends(get_current_workspace),
    session: Session = Depends(get_db_session),
):
    """列出当前工作空间下的所有模型配置"""
    statement = select(LLMModelConfig).where(LLMModelConfig.workspace_id == workspace.id)
    results = session.exec(statement).all()

    # 转换为 Read Schema，计算 has_api_key
    return [LLMModelConfigRead(**m.model_dump(), has_api_key=m.encrypted_api_key is not None) for m in results]


@router.post("/", response_model=LLMModelConfigRead)
async def create_model(
    config_in: LLMModelConfigCreate,
    workspace: Workspace = Depends(get_current_workspace),
    session: Session = Depends(get_db_session),
):
    """创建一个新的模型配置"""
    # EncryptedString type automatically encrypts the value when saved to database
    encrypted_key = config_in.api_key

    # 2. 创建 DB 对象
    db_obj = LLMModelConfig(
        **config_in.model_dump(exclude={"api_key"}),  # 排除明文 Key
        encrypted_api_key=encrypted_key,
        workspace_id=workspace.id,
    )

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)

    return LLMModelConfigRead(**db_obj.model_dump(), has_api_key=encrypted_key is not None)


@router.patch("/{model_id}", response_model=LLMModelConfigRead)
async def update_model(
    model_id: UUID,
    config_in: LLMModelConfigUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    session: Session = Depends(get_db_session),
):
    """更新模型配置"""
    db_obj = session.get(LLMModelConfig, model_id)
    if not db_obj or db_obj.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Model config not found")

    update_data = config_in.model_dump(exclude_unset=True)

    # Special handling for API Key: EncryptedString type automatically encrypts at database layer
    if "api_key" in update_data:
        raw_key = update_data.pop("api_key")
        if raw_key:
            db_obj.encrypted_api_key = raw_key
        # If empty string or None passed, keep existing key (don't modify)

    for key, value in update_data.items():
        setattr(db_obj, key, value)

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)

    return LLMModelConfigRead(**db_obj.model_dump(), has_api_key=db_obj.encrypted_api_key is not None)


@router.delete("/{model_id}")
async def delete_model(
    model_id: UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: Session = Depends(get_db_session),
):
    db_obj = session.get(LLMModelConfig, model_id)
    if not db_obj or db_obj.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Model config not found")

    session.delete(db_obj)
    session.commit()
    return {"ok": True}


# --- 核心：测试连接 ---


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(
    test_data: TestConnectionRequest,
    user: User = Depends(get_current_user),
):
    """
    无状态测试：前端把填好的表单发过来（含明文 Key），
    后端尝试调用 LiteLLM，不保存入库。
    """
    try:
        start_time = time.time()

        # 构造 LiteLLM 参数
        # 注意：这里我们手动组装参数，因为 test_data 是 Pydantic 模型
        model_name = test_data.model
        if test_data.provider != "openai":
            # LiteLLM 格式: provider/model_name
            model_name = f"{test_data.provider}/{test_data.model}"

        # 准备一次极简的调用
        response = await litellm.acompletion(
            model=model_name,
            messages=[{"role": "user", "content": "Hello"}],
            api_key=test_data.api_key,
            base_url=test_data.api_base,
            api_version=test_data.api_version,
            max_tokens=5,  # 只要能通就行，省钱
            **test_data.parameters,
        )

        duration = (time.time() - start_time) * 1000
        return TestConnectionResponse(success=True, latency_ms=round(duration, 2), message="Connection successful! Model responded.")

    except Exception as e:
        # LiteLLM 的报错通常比较详细，直接返回给前端用于 Debug
        return TestConnectionResponse(success=False, latency_ms=0, message=f"Connection failed: {str(e)}")
