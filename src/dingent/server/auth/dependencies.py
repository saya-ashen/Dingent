import json
from uuid import uuid4
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from dingent.server.db.crud import PROD_FAKE_USERS_DB, get_user
from .schemas import UserPublic
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# TODO: This should be moved to a proper database


def fake_decode_token(token):
    """Fallback token decoder for testing."""
    return UserPublic(
        username="admin_456",
        email="john@example.com",
        full_name="John Doe",
        id=str(uuid4()),
        role=["admin"],
    )


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserPublic:
    """Extract and validate current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub", "unknown")
    if username is None:
        raise credentials_exception

    user_data = get_user(PROD_FAKE_USERS_DB, username)
    if user_data is None:
        raise credentials_exception

    # Convert dictionary to Pydantic model
    return UserPublic(**user_data)
