import json
import re
from fastapi import Depends, HTTPException, Request
from .schemas import UserPublic
from .dependencies import get_current_user


# TODO: This should be moved to a proper database
FAKE_THREADS_DB = {
    "thread_abc": {"id": "thread_abc", "owner_id": "user_123"},
    "thread_def": {"id": "thread_def", "owner_id": "admin_456"},
}


async def dynamic_authorizer(request: Request, user: UserPublic = Depends(get_current_user)):
    """
    Dynamic authorization based on the request path and user permissions.
    This authorizer examines the request path and enforces permissions accordingly.
    """
    # Extract path from request parameters (matching original handler logic)
    path = request.path_params.get("path", "")

    # Rule 1: Match /agent/{name}/state (read access)
    if re.match(r"agent/([a-zA-Z0-9_-]+)/state", path):
        # Permission: Allow anonymous read access
        pass

    # Rule 2: Match /agent/{name} (execution)
    elif re.match(r"agent/([a-zA-Z0-9_-]+)", path):
        # Permission: Must be logged in user and thread owner
        if user.role == "anonymous":
            raise HTTPException(status_code=403, detail="Anonymous users are not allowed to execute agents.")

        # Check thread ownership
        try:
            body = await request.json()
            thread_id = body.get("threadId")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body for execution request.")

        if thread_id:
            # If thread_id is provided, verify ownership
            thread_info = FAKE_THREADS_DB.get(thread_id)
            if not thread_info or thread_info["owner_id"] != user.id:
                raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found or you do not have permission to access it.")

    # Rule 3: Match /action/{name} (action execution)
    elif re.match(r"action/([a-zA-Z0-9_-]+)", path):
        # Permission: Must be logged in user
        if user.role == "anonymous":
            raise HTTPException(status_code=403, detail="Anonymous users are not allowed to execute actions.")

    # Default rule: Allow other paths to pass through
    else:
        pass

    return user


class Authorizer:
    """
    Permission-based authorizer that checks for specific required permissions.
    """

    def __init__(self, required_permissions: list[str]):
        """
        Initialize with required permissions.
        Example: ["agent:read"] or ["agent:execute", "thread:owner"]
        """
        self.required_permissions = set(required_permissions)

    async def __call__(self, request: Request, user: UserPublic = Depends(get_current_user)):
        # Check agent read permission
        if "agent:read" in self.required_permissions:
            # Any user (including anonymous) can read
            pass

        # Check agent execute permission
        if "agent:execute" in self.required_permissions:
            if user.role == "guest":
                raise HTTPException(status_code=403, detail="Anonymous users are not allowed to execute agents.")

        # Check thread ownership permission
        if "thread:owner" in self.required_permissions:
            if user.role == "guest":
                raise HTTPException(status_code=403, detail="You must be logged in to perform this action.")

            try:
                body = await request.json()
                thread_id = body.get("threadId")
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON body")

            if not thread_id:
                raise HTTPException(status_code=400, detail="threadId is required for this operation.")

            thread_info = FAKE_THREADS_DB.get(thread_id)
            if not thread_info or thread_info["owner_id"] != user.id:
                raise HTTPException(
                    status_code=404,
                    detail=f"Thread '{thread_id}' not found or you do not have permission to access it.",
                )

        return user
