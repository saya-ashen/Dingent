from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from dingent.core.db.models import User, Workspace, WorkspaceMember


def create_workspace_for_user(db: Session, *, user: User, name: str, description: str | None = None) -> Workspace:
    """
    创建一个新的工作空间，并将该用户设为 Owner。
    必须在一个事务中完成。
    """
    # 1. 创建 Workspace 对象
    workspace = Workspace(name=name, description=description)
    db.add(workspace)

    member_link = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    db.add(member_link)

    try:
        db.commit()
        db.refresh(workspace)
    except Exception as e:
        db.rollback()
        raise e

    return workspace


def add_user_to_workspace(db: Session, *, workspace_id: UUID, email: str, role: str = "member") -> WorkspaceMember:
    """
    通过邮箱邀请用户加入工作空间
    """
    # 1. 查找用户是否存在
    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. 检查是否已经在组内
    existing = db.get(WorkspaceMember, (workspace_id, user.id))
    if existing:
        raise HTTPException(status_code=409, detail="User already in workspace")

    # 3. 添加关联
    new_member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=role)
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


def get_user_workspaces(db: Session, user_id: UUID) -> list[Workspace]:
    """
    查询某个用户加入了哪些工作空间
    """
    # 这种多对多查询在 SQLModel 中可以通过 User.workspaces 关系直接获取
    # 或者手动 join 查询以便获取 role 信息
    user = db.get(User, user_id)
    return user.workspaces if user else []


def get_specific_user_workspace(db: Session, user_id: UUID, workspace_id: UUID) -> Workspace | None:
    """
    获取特定用户的特定 Workspace。
    如果用户不是该 Workspace 的成员，或者 Workspace 不存在，都返回 None。
    """
    statement = select(Workspace).join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id).where(Workspace.id == workspace_id)

    # 执行查询
    result = db.exec(statement).first()

    return result


def get_workspace_allow_guest(db: Session, workspace_id: UUID) -> Workspace | None:
    """
    获取公开的 Workspace。
    如果 Workspace 不存在或不是公开的，返回 None。
    """
    statement = select(Workspace).where(Workspace.id == workspace_id).where(Workspace.allow_guest_access == True)

    result = db.exec(statement).first()

    return result
