from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
import random
import string
import json
from typing import List, Optional
from src.app.core.config import settings, get_redis
from src.app.models.url import URL
from src.app.schemas.url import URLCreate, URLUpdate


def generate_short_code(length: int = 6) -> str:
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def serialize_url(url: URL) -> dict:
    """Convert SQLAlchemy URL model to dictionary."""
    return {
        "id": url.id,
        "original_url": url.original_url,
        "short_code": url.short_code,
        "expires_at": url.expires_at.isoformat() if url.expires_at else None,
        "visits": url.visits,
        "last_visited_at": url.last_visited_at.isoformat()
        if url.last_visited_at
        else None,
        "user_id": url.user_id,
        "created_at": url.created_at.isoformat() if url.created_at else None,
        "updated_at": url.updated_at.isoformat() if url.updated_at else None,
    }


def get_url_by_short_code(db: Session, short_code: str) -> Optional[URL]:
    return db.query(URL).filter(URL.short_code == short_code).first()


def create_short_url(
    db: Session, url_data: URLCreate, user_id: Optional[int] = None
) -> URL:
    short_code = url_data.custom_alias or generate_short_code(
        settings.SHORT_CODE_LENGTH
    )

    if get_url_by_short_code(db, short_code):
        raise ValueError("Short code already exists")

    original_url_str = str(url_data.original_url)

    db_url = URL(
        original_url=original_url_str,
        short_code=short_code,
        expires_at=url_data.expires_at,
        user_id=user_id,
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)

    try:
        redis = get_redis()
        redis.setex(
            f"url:{short_code}",
            int(timedelta(days=settings.DEFAULT_EXPIRY_DAYS).total_seconds()),
            json.dumps(serialize_url(db_url)),
        )
    except Exception as e:
        print(f"Redis error: {e}")

    return db_url


def update_url(db: Session, short_code: str, url_data: URLUpdate) -> Optional[URL]:
    db_url = get_url_by_short_code(db, short_code)
    if not db_url:
        return None

    update_data = url_data.model_dump(exclude_unset=True)

    if "original_url" in update_data and update_data["original_url"] is not None:
        update_data["original_url"] = str(update_data["original_url"])

    for field, value in update_data.items():
        setattr(db_url, field, value)

    db.commit()
    db.refresh(db_url)

    try:
        redis = get_redis()
        redis.setex(
            f"url:{short_code}",
            int(timedelta(days=settings.DEFAULT_EXPIRY_DAYS).total_seconds()),
            json.dumps(serialize_url(db_url)),
        )
    except Exception as e:
        print(f"Redis error: {e}")

    return db_url


def delete_url(db: Session, short_code: str) -> bool:
    db_url = get_url_by_short_code(db, short_code)
    if not db_url:
        return False

    db.delete(db_url)
    db.commit()

    try:
        redis = get_redis()
        redis.delete(f"url:{short_code}")
    except Exception as e:
        print(f"Redis error: {e}")

    return True


def increment_visits(db: Session, short_code: str) -> Optional[URL]:
    db_url = get_url_by_short_code(db, short_code)
    if not db_url:
        return None

    db_url.visits += 1
    db_url.last_visited_at = datetime.now(UTC)
    db.commit()
    db.refresh(db_url)

    try:
        redis = get_redis()
        redis.setex(
            f"url:{short_code}",
            int(timedelta(days=settings.DEFAULT_EXPIRY_DAYS).total_seconds()),
            json.dumps(serialize_url(db_url)),
        )
    except Exception as e:
        print(f"Redis error: {e}")

    return db_url


def get_url_stats(db: Session, short_code: str) -> Optional[URL]:
    return get_url_by_short_code(db, short_code)


def search_urls(db: Session, original_url: str) -> List[URL]:
    return db.query(URL).filter(URL.original_url.ilike(f"%{original_url}%")).all()


def cleanup_expired_urls(db: Session) -> int:
    expired_urls = (
        db.query(URL)
        .filter(URL.expires_at <= datetime.now(UTC), URL.expires_at.isnot(None))
        .all()
    )

    try:
        redis = get_redis()
        for url in expired_urls:
            db.delete(url)
            redis.delete(f"url:{url.short_code}")
    except Exception as e:
        print(f"Redis error: {e}")
        for url in expired_urls:
            db.delete(url)

    db.commit()
    return len(expired_urls)
