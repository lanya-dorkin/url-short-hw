from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
from jose import jwt
from passlib.context import CryptContext
from typing import Optional
import json

from src.app.core.config import settings, get_redis
from src.app.models.user import User
from src.app.schemas.user import UserCreate, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
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
        redis.setex(
            f"token:{encoded_jwt}",
            int(expire.timestamp() - datetime.now(UTC).timestamp()),
            data.get("sub", ""),
        )
    except Exception as e:
        print(f"Redis error: {e}")

    return encoded_jwt


def serialize_user(user: User) -> dict:
    """Convert SQLAlchemy User model to dictionary."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def get_user_by_email(db: Session, email: str) -> Optional[User]:
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
            print(f"Redis error: {e}")

    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
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
            print(f"Redis error: {e}")

    return user


def create_user(db: Session, user: UserCreate) -> User:
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
        print(f"Redis error: {e}")

    return db_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, username) or get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_user(db: Session, user: User, user_update: UserUpdate) -> User:
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
        print(f"Redis error: {e}")

    return user


def invalidate_user_cache(user: User):
    redis = get_redis()
    redis.delete(f"user:email:{user.email}")
    redis.delete(f"user:username:{user.username}")
