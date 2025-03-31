from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from datetime import datetime, UTC

from src.app.core.config import settings, get_redis, logger
from src.app.db.session import get_db
from src.app.services.user_service import get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/login")


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    """
    Get the current authenticated user from the provided JWT token.

    Args:
        db: Database session
        token: JWT token from authorization header

    Returns:
        The authenticated user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        redis = get_redis()
        
        if redis:
            is_blacklisted = redis.exists(f"blacklist:token:{token}")
            if is_blacklisted:
                logger.warning("Attempt to use blacklisted token")
                raise credentials_exception
                
        if redis:
            token_in_cache = redis.get(f"token:{token}")
            if not token_in_cache:
                logger.warning("Token not found in cache")

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token has no subject claim")
            raise credentials_exception

        user = get_user_by_username(db, username=username)
        if user is None:
            logger.warning(f"User not found: {username}")
            raise credentials_exception

        if redis and not token_in_cache:
            exp = payload.get("exp")
            if exp:
                ttl = max(1, int(exp - datetime.now(UTC).timestamp()))
                redis.setex(f"token:{token}", ttl, username)

        return user
    except JWTError as e:
        logger.warning(f"JWT validation error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception


def get_current_active_user(current_user=Depends(get_current_user)):
    """
    Get the current authenticated user and verify they are active.

    Args:
        current_user: User from get_current_user

    Returns:
        The active authenticated user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
