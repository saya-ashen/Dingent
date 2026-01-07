from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, func, select

from dingent.core.db.models import User, Workspace, WorkspaceMember
from dingent.core.schemas import WorkspaceCreate, WorkspaceInvite, WorkspaceMemberRead, WorkspaceRead, WorkspaceUpdate


class UserWorkspaceService:
    def __init__(self, session: Session, user_id: UUID):
        self.session = session
        self.user_id = user_id

    def _get_workspace_context(self, slug: str) -> tuple[Workspace, WorkspaceMember]:
        """
        Helper: 根据 Slug 查找工作空间，同时获取当前用户的成员信息。
        如果找不到空间，或者用户不在空间内，统一返回 404 (隐式鉴权)。
        返回: (Workspace 对象, 当前用户的 WorkspaceMember 对象)
        """
        statement = (
            select(Workspace, WorkspaceMember)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(Workspace.slug == slug, WorkspaceMember.user_id == self.user_id)
        )
        result = self.session.exec(statement).first()

        if not result:
            # 这里的 404 既可能是 slug 不存在，也可能是用户没权限
            # 这种模糊处理更安全，防止枚举 slug
            raise HTTPException(status_code=404, detail="Workspace not found")

        return result

    def list_workspaces(self) -> list[WorkspaceRead]:
        """列出当前用户加入的所有工作空间"""
        statement = select(Workspace, WorkspaceMember.role).join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == self.user_id)
        results = self.session.exec(statement).all()

        workspaces = []
        for ws, role in results:
            # 统计成员数量
            member_count = self.session.exec(select(func.count(WorkspaceMember.user_id)).where(WorkspaceMember.workspace_id == ws.id)).one()

            workspaces.append(
                WorkspaceRead(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,  # ✅ 新增
                    description=ws.description,
                    created_at=ws.created_at,
                    role=role,
                    member_count=member_count,
                    allow_guest_access=ws.allow_guest_access,
                )
            )
        return workspaces

    def create_workspace(self, payload: WorkspaceCreate) -> WorkspaceRead:
        """创建新空间 (payload 中必须包含 slug)"""

        # 0. 检查 Slug 是否被占用 (全局唯一)
        # 注意：这只是应用层检查，数据库层也应该有 unique constraint
        existing_slug = self.session.exec(select(Workspace).where(Workspace.slug == payload.slug)).first()
        if existing_slug:
            raise HTTPException(status_code=409, detail="Workspace identifier (slug) is already taken.")

        # 1. 创建 Workspace
        workspace = Workspace(
            name=payload.name,
            slug=payload.slug,  # ✅ 写入 slug
            description=payload.description,
        )
        self.session.add(workspace)
        self.session.flush()  # 获取 ID

        # 2. 添加 Owner
        member = WorkspaceMember(workspace_id=workspace.id, user_id=self.user_id, role="owner")
        self.session.add(member)
        self.session.commit()
        self.session.refresh(workspace)

        return WorkspaceRead(
            id=workspace.id, name=workspace.name, slug=workspace.slug, description=workspace.description, created_at=workspace.created_at, role="owner", member_count=1
        )

    def get_workspace(self, slug: str) -> WorkspaceRead:
        workspace, member = self._get_workspace_context(slug)

        # 统计成员数
        count = self.session.exec(select(func.count(WorkspaceMember.user_id)).where(WorkspaceMember.workspace_id == workspace.id)).one()

        return WorkspaceRead(
            id=workspace.id,
            name=workspace.name,
            slug=workspace.slug,  # ✅
            description=workspace.description,
            created_at=workspace.created_at,
            role=member.role,
            member_count=count,
            allow_guest_access=workspace.allow_guest_access,
        )

    def update_workspace(self, slug: str, payload: WorkspaceUpdate) -> WorkspaceRead:
        workspace, member = self._get_workspace_context(slug)

        # 鉴权
        if member.role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Only admins can update workspace settings")

        if payload.name:
            workspace.name = payload.name
        if payload.description is not None:
            workspace.description = payload.description
        if payload.allow_guest_access is not None:
            workspace.allow_guest_access = payload.allow_guest_access

        self.session.add(workspace)
        self.session.commit()
        self.session.refresh(workspace)

        return self.get_workspace(slug)

    def invite_member(self, slug: str, payload: WorkspaceInvite) -> WorkspaceMemberRead:
        workspace, member = self._get_workspace_context(slug)

        if member.role not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Only admins can invite members")

        # 1. 查找目标用户
        target_user = self.session.exec(select(User).where(User.email == payload.email)).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="User with this email does not exist")

        # 2. 检查是否已经在空间内
        existing = self.session.exec(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.user_id == target_user.id)).first()

        if existing:
            raise HTTPException(status_code=409, detail="User is already in this workspace")

        # 3. 添加成员
        new_member = WorkspaceMember(
            workspace_id=workspace.id,  # ✅ 使用从 context 中拿到的 ID
            user_id=target_user.id,
            role=payload.role,
        )
        self.session.add(new_member)
        self.session.commit()

        return WorkspaceMemberRead(
            user_id=target_user.id, email=target_user.email, username=target_user.username, avatar_url=target_user.avatar_url, role=new_member.role, joined_at=new_member.joined_at
        )

    def list_members(self, slug: str) -> list[WorkspaceMemberRead]:
        workspace, _ = self._get_workspace_context(slug)  # 鉴权

        statement = (
            select(WorkspaceMember, User).join(User, WorkspaceMember.user_id == User.id).where(WorkspaceMember.workspace_id == workspace.id)  # ✅ 使用 workspace.id
        )
        results = self.session.exec(statement).all()

        members = []
        for mem, user in results:
            members.append(WorkspaceMemberRead(user_id=user.id, email=user.email, username=user.username, avatar_url=user.avatar_url, role=mem.role, joined_at=mem.joined_at))
        return members

    def remove_member(self, slug: str, target_user_id: UUID) -> None:
        # 1. 获取操作者(Operator)的上下文
        workspace, operator_member = self._get_workspace_context(slug)

        # 2. 获取目标(Target)的成员记录
        # 注意：这里我们有了 workspace.id，所以可以直接查 member 表
        target_member = self.session.exec(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.user_id == target_user_id)).first()

        if not target_member:
            raise HTTPException(status_code=404, detail="Member not found")

        # 3. 权限校验逻辑 (保持不变)
        is_self_leaving = self.user_id == target_user_id

        if not is_self_leaving:
            if operator_member.role == "member":
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            if operator_member.role == "admin" and target_member.role in ["admin", "owner"]:
                raise HTTPException(status_code=403, detail="Admins cannot remove other admins or owners")

        # 4. 防止删除最后一个 Owner
        if target_member.role == "owner":
            # 统计该空间下的 owner 数量
            owner_count = self.session.exec(select(func.count(WorkspaceMember.user_id)).where(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.role == "owner")).one()

            if owner_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last owner of a workspace")

        self.session.delete(target_member)
        self.session.commit()
