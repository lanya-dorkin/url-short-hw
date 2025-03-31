from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
from jose import jwt
from passlib.context import CryptContext
from typing import Optional
import json

from src.app.core.config import settings, get_redis, logger
from src.app.models.user import User
from src.app.schemas.user import UserCreate, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to compare against

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password for storage.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time, defaults to 15 minutes

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    try:
        redis = get_redis()
        token_ttl = int(expire.timestamp() - datetime.now(UTC).timestamp())
        redis.setex(
            f"token:{encoded_jwt}",
            token_ttl,
            data.get("sub", ""),
        )
        logger.info(f"Token cached for user {data.get('sub')} with TTL of {token_ttl} seconds")
    except Exception as e:
        logger.error(f"Redis error when caching token: {e}")

    return encoded_jwt


def serialize_user(user: User) -> dict:
    """
    Convert SQLAlchemy User model to dictionary for caching.

    Args:
        user: User model instance

    Returns:
        Dictionary representation of user with ISO-formatted dates
    """
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "hashed_password": user.hashed_password,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def deserialize_user(data: dict) -> User:
    user = User(
        id=data["id"],
        email=data["email"],
        username=data["username"],
        is_active=data["is_active"],
        hashed_password=data["hashed_password"],
    )

    if data["created_at"]:
        user.created_at = datetime.fromisoformat(data["created_at"])

    if data["updated_at"]:
        user.updated_at = datetime.fromisoformat(data["updated_at"])

    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get user by email from database or cache.

    Args:
        db: Database session
        email: Email to look up

    Returns:
        User object if found, None otherwise
    """
    try:
        redis = get_redis()
        cached_user_json = redis.get(f"user:email:{email}")
        if cached_user_json:
            cached_user_data = json.loads(cached_user_json)
            return deserialize_user(cached_user_data)
    except Exception as e:
        logger.error(f"Redis error: {e}")

    user = db.query(User).filter(User.email == email).first()

    if user:
        try:
            redis = get_redis()
            redis.setex(
                f"user:email:{email}",
                3600,  # Cache for 1 hour
                json.dumps(serialize_user(user)),
            )
        except Exception as e:
            logger.error(f"Redis error: {e}")

    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Get user by username from database or cache.

    Args:
        db: Database session
        username: Username to look up

    Returns:
        User object if found, None otherwise
    """
    try:
        redis = get_redis()
        cached_user_json = redis.get(f"user:username:{username}")
        if cached_user_json:
            cached_user_data = json.loads(cached_user_json)
            return deserialize_user(cached_user_data)
    except Exception as e:
        logger.error(f"Redis error: {e}")

    user = db.query(User).filter(User.username == username).first()

    if user:
        try:
            redis = get_redis()
            redis.setex(
                f"user:username:{username}",
                3600,
                json.dumps(serialize_user(user)),
            )
        except Exception as e:
            logger.error(f"Redis error: {e}")

    return user


def create_user(db: Session, user: UserCreate) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        user: User creation data

    Returns:
        Created user object

    Raises:
        ValueError: If email already registered or username already taken
    """
    if get_user_by_email(db, user.email):
        raise ValueError("Email already registered")
    if get_user_by_username(db, user.username):
        raise ValueError("Username already taken")

    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email, username=user.username, hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    try:
        redis = get_redis()
        redis.setex(
            f"user:email:{db_user.email}", 3600, json.dumps(serialize_user(db_user))
        )
        redis.setex(
            f"user:username:{db_user.username}",
            3600,
            json.dumps(serialize_user(db_user)),
        )
    except Exception as e:
        logger.error(f"Redis error: {e}")

    return db_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username/email and password.

    Args:
        db: Database session
        username: Username or email
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    user = get_user_by_email(db, username) or get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_user(db: Session, user: User, user_update: UserUpdate) -> User:
    """
    Update user data.

    Args:
        db: Database session
        user: User object to update
        user_update: Update data

    Returns:
        Updated user object
    """
    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    try:
        redis = get_redis()
        redis.setex(f"user:email:{user.email}", 3600, json.dumps(serialize_user(user)))
        redis.setex(
            f"user:username:{user.username}", 3600, json.dumps(serialize_user(user))
        )
    except Exception as e:
        logger.error(f"Redis error: {e}")

    return user


def invalidate_user_cache(user: User):
    """
    Remove user data from cache.

    Args:
        user: User object whose cache entries to invalidate
    """
    try:
        redis = get_redis()
        redis.delete(f"user:email:{user.email}")
        redis.delete(f"user:username:{user.username}")
    except Exception as e:
        logger.error(f"Redis error: {e}")


def invalidate_token(token: str):
    """
    Invalidate a JWT token by removing it from cache.

    Args:
        token: JWT token to invalidate
    """
    try:
        redis = get_redis()
        redis.delete(f"token:{token}")
        logger.info("Token successfully invalidated")
    except Exception as e:
        logger.error(f"Redis error when invalidating token: {e}")
        
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        exp = payload.get("exp")
        
        if username and exp:
            redis = get_redis()
            ttl = max(1, int(exp - datetime.now(UTC).timestamp()))
            redis.setex(f"blacklist:token:{token}", ttl, "1")
            logger.info(f"Token added to blacklist for {ttl} seconds")
    except Exception as e:
        logger.error(f"Error adding token to blacklist: {e}")
