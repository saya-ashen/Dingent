from sqlmodel import Session, select

from dingent.core.db.models import Role, User, Workspace, WorkspaceMember
from dingent.core.schemas import UserCreate


def get_user(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    result = session.exec(statement).first()
    return result


def create_user(session: Session, user_in: UserCreate) -> User:
    """
    接收 Pydantic 模型，处理密码加密，保存到数据库，并创建默认工作空间。
    """
    from dingent.server.auth.security import get_password_hash

    # 1. 密码加密逻辑
    hashed_pw = get_password_hash(user_in.password)

    # 2. 创建用户对象
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
    )

    # 分配默认角色 (系统级角色，如 standard user)
    default_role_name = "user"
    statement = select(Role).where(Role.name == default_role_name)
    role_obj = session.exec(statement).first()
    if not role_obj:
        raise ValueError(f"系统错误：默认角色 '{default_role_name}' 未在数据库中创建。")
    db_user.roles.append(role_obj)

    session.add(db_user)
    # 注意：这里先 flush 以获取 db_user.id，但不 commit，保证原子性
    session.flush()

    # --- 新增：自动创建默认工作空间 ---

    # 3. 创建个人工作空间
    default_workspace = Workspace(
        name=f"{user_in.username}'s Workspace",
        slug=f"user-{db_user.id}-workspace",
        description="Default personal workspace",
    )
    session.add(default_workspace)
    # flush 以获取 workspace.id
    session.flush()

    # 4. 将用户设为该空间的 Owner
    member_link = WorkspaceMember(workspace_id=default_workspace.id, user_id=db_user.id, role="owner")
    session.add(member_link)

    # 5. 统一提交
    session.commit()
    session.refresh(db_user)

    return db_user
