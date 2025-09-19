# dingent/server/api/routers/auth.py

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session  # Import Session for dependency

from ...auth import security
from ...db import crud, database  # Import your CRUD functions and get_db
from ...schemas.token import Token  # Import the Token schema

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(database.get_db),  # Use your real get_db dependency
):
    # 1. Call the authentication logic from the crud/service layer
    #    Note: We pass the db session to the function now.
    user = crud.authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Create the JWT
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # "sub" (subject) should be the user's unique identifier, email is a good choice.
    access_token = security.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    # 3. Return the response using the user object returned from crud
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            # You can add any other fields you want the frontend to have
        },
    }
