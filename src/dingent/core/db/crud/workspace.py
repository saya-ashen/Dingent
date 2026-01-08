from uuid import UUID

from sqlmodel import Session, col, select

from dingent.core.db.models import User, Workspace, WorkspaceMember


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
    statement = (
        select(Workspace).join(WorkspaceMember, col(Workspace.id) == WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id).where(Workspace.id == workspace_id)
    )

    # 执行查询
    result = db.exec(statement).first()

    return result


def get_workspace_allow_guest(session, workspace_id: UUID) -> Workspace | None:
    """
    获取公开的 Workspace。
    如果 Workspace 不存在或不是公开的，返回 None。
    """
    statement = select(Workspace).where(Workspace.id == workspace_id).where(col(Workspace.allow_guest_access).is_(True))

    result = session.exec(statement).first()

    return result
