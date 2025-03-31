from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC
import random
import string
import json
from typing import List, Optional
from src.app.core.config import settings, get_redis, logger
from src.app.models.url import URL
from src.app.schemas.url import URLCreate, URLUpdate


def generate_short_code(length: int = 6) -> str:
    """
    Generate a random short code of specified length.

    Args:
        length: Length of the short code to generate, defaults to 6

    Returns:
        A random string with mixed case letters and digits
    """
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def serialize_url(url: URL) -> dict:
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


def deserialize_url(data: dict) -> URL:
    url = URL(
        id=data["id"],
        original_url=data["original_url"],
        short_code=data["short_code"],
        visits=data["visits"],
        user_id=data["user_id"],
    )

    if data["expires_at"]:
        url.expires_at = datetime.fromisoformat(data["expires_at"])

    if data["last_visited_at"]:
        url.last_visited_at = datetime.fromisoformat(data["last_visited_at"])

    if data["created_at"]:
        url.created_at = datetime.fromisoformat(data["created_at"])

    if data["updated_at"]:
        url.updated_at = datetime.fromisoformat(data["updated_at"])

    return url


def get_url_by_short_code(db: Session, short_code: str) -> Optional[URL]:
    """
    Get URL by short code from database or cache.

    Args:
        db: Database session
        short_code: Short code to look up

    Returns:
        URL object if found, None otherwise
    """
    try:
        redis = get_redis()
        cached_url_json = redis.get(f"url:{short_code}")

        if cached_url_json:
            cached_url_data = json.loads(cached_url_json)
            return deserialize_url(cached_url_data)
    except Exception as e:
        logger.error(f"Redis error: {e}")

    return db.query(URL).filter(URL.short_code == short_code).first()


def create_short_url(
    db: Session, url_data: URLCreate, user_id: Optional[int] = None
) -> URL:
    """
    Create a new shortened URL.

    Args:
        db: Database session
        url_data: URL creation data including original URL and optional custom alias
        user_id: ID of the user creating the URL, or None for anonymous

    Returns:
        Created URL object

    Raises:
        ValueError: If short code already exists
    """
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
        logger.error(f"Redis error: {e}")

    return db_url


def update_url(db: Session, short_code: str, url_data: URLUpdate) -> Optional[URL]:
    """
    Update an existing URL.

    Args:
        db: Database session
        short_code: Short code of URL to update
        url_data: Update data containing new original URL or expiration

    Returns:
        Updated URL object or None if not found
    """
    db_url = db.query(URL).filter(URL.short_code == short_code).first()
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
        logger.error(f"Redis error: {e}")

    return db_url


def delete_url(db: Session, short_code: str) -> bool:
    """
    Delete a URL by short code.

    Args:
        db: Database session
        short_code: Short code of URL to delete

    Returns:
        True if deleted, False if not found
    """
    db_url = db.query(URL).filter(URL.short_code == short_code).first()
    if not db_url:
        return False

    db.delete(db_url)
    db.commit()

    try:
        redis = get_redis()
        redis.delete(f"url:{short_code}")
    except Exception as e:
        logger.error(f"Redis error: {e}")

    return True


def increment_visits(db: Session, short_code: str) -> Optional[URL]:
    """
    Increment visit counter for a URL.

    Args:
        db: Database session
        short_code: Short code of URL to increment

    Returns:
        Updated URL object or None if not found
    """
    db_url = db.query(URL).filter(URL.short_code == short_code).first()
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
        logger.error(f"Redis error: {e}")

    return db_url


def get_url_stats(db: Session, short_code: str) -> Optional[URL]:
    """
    Get URL statistics.

    Args:
        db: Database session
        short_code: Short code of URL to get stats for

    Returns:
        URL object with stats or None if not found
    """
    return get_url_by_short_code(db, short_code)


def search_urls(db: Session, original_url: str, limit: int = 10, offset: int = 0) -> List[URL]:
    """
    Search for URLs by original URL (partial match) with pagination.

    Args:
        db: Database session
        original_url: Original URL to search for
        limit: Maximum number of results to return
        offset: Offset for pagination

    Returns:
        List of matching URL objects
    """
    return (
        db.query(URL)
        .filter(URL.original_url.ilike(f"%{original_url}%"))
        .order_by(URL.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def cleanup_expired_urls(db: Session) -> int:
    """
    Delete URLs that have expired.

    Args:
        db: Database session

    Returns:
        Number of URLs deleted
    """
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
        logger.error(f"Redis error: {e}")
        for url in expired_urls:
            db.delete(url)

    db.commit()
    return len(expired_urls)


def cleanup_unused_links(db: Session, days: int) -> int:
    """
    Delete URLs that haven't been used for specified number of days.

    Args:
        db: Database session
        days: Number of days of inactivity before deletion

    Returns:
        Number of URLs deleted
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    unused_urls = (
        db.query(URL)
        .filter(
            (URL.last_visited_at <= cutoff_date)
            | (URL.last_visited_at.is_(None) & (URL.created_at <= cutoff_date))
        )
        .all()
    )

    redis = get_redis()
    for url in unused_urls:
        db.delete(url)
        try:
            redis.delete(f"url:{url.short_code}")
        except Exception as e:
            logger.error(f"Redis error: {e}")

    db.commit()
    return len(unused_urls)


def get_expired_urls_history(
    db: Session, limit: int = 100, offset: int = 0
) -> List[URL]:
    """
    Get history of expired URLs.

    Args:
        db: Database session
        limit: Maximum number of results to return
        offset: Offset for pagination

    Returns:
        List of expired URL objects
    """
    return (
        db.query(URL)
        .filter(URL.expires_at <= datetime.now(UTC), URL.expires_at.isnot(None))
        .order_by(URL.expires_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
