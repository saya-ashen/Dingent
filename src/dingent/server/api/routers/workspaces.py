from datetime import datetime
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, Response, status, HTTPException

# 引入新的 Schema
from dingent.core.schemas import (
    WorkspaceCreate,
    WorkspaceInvite,
    WorkspaceMemberRead,
    WorkspaceRead,
    WorkspaceRole,
    WorkspaceUpdate,
    WorkspaceWithRole,  # 👈 引入这个新模型
)

from dingent.server.services.user_workspace_service import UserWorkspaceService
from dingent.server.api.dependencies import get_user_workspace_service

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=list[WorkspaceRead])
async def list_my_workspaces(service: UserWorkspaceService = Depends(get_user_workspace_service)):
    """List all workspaces the current user belongs to."""
    return service.list_workspaces()


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreate, service: UserWorkspaceService = Depends(get_user_workspace_service)):
    """Create a new workspace."""
    # 注意：service.create_workspace 内部需要处理 slug 的生成或唯一性校验
    return service.create_workspace(payload)


# --- Single Resource Operations (核心修改) ---


@router.get("/{slug}", response_model=WorkspaceWithRole)  # 👈 返回模型变了
async def get_workspace(slug: str, service: UserWorkspaceService = Depends(get_user_workspace_service)):  # 👈 参数变了
    """
    Get workspace by slug.
    Implicitly checks if current user is a member.
    Returns workspace details + user's role.
    """
    # Service 层需要实现 get_by_slug
    workspace = service.get_workspace(slug)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.patch("/{slug}", response_model=WorkspaceRead)
async def update_workspace(slug: str, payload: WorkspaceUpdate, service: UserWorkspaceService = Depends(get_user_workspace_service)):
    """Update workspace settings using slug."""
    return service.update_workspace(slug, payload)


@router.get("/{slug}/members", response_model=list[WorkspaceMemberRead])
async def list_members(slug: str, service: UserWorkspaceService = Depends(get_user_workspace_service)):
    return service.list_members(slug)


@router.post("/{slug}/members", response_model=WorkspaceMemberRead)
async def invite_member(slug: str, payload: WorkspaceInvite, service: UserWorkspaceService = Depends(get_user_workspace_service)):
    return service.invite_member(slug, payload)


@router.delete("/{slug}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(slug: str, user_id: UUID, service: UserWorkspaceService = Depends(get_user_workspace_service)):
    """
    Remove a member from the workspace identified by slug.
    """
    service.remove_member(slug, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
