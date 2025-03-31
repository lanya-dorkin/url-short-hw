from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.app.api.deps import get_db, get_current_active_user
from src.app.core.config import settings
from src.app.schemas.user import User, UserCreate, Token
from src.app.services.user_service import (
    create_user,
    authenticate_user,
    create_access_token,
    invalidate_token,
)

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Creates a new user with the provided email, username, and password.
    """
    try:
        db_user = create_user(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Login with username/email and password.

    Returns a JWT access token for use in authenticating subsequent requests.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(token: str = Depends(security)):
    """
    Logout by invalidating the current access token.

    Requires a valid JWT token which will be invalidated.
    """
    invalidate_token(token.credentials)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=User)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.

    Requires authentication.
    """
    return current_user
