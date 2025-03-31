from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.app.api.deps import get_db, get_current_active_user
from src.app.schemas.url import URL, URLCreate, URLUpdate, URLStats
from src.app.services.url_service import (
    create_short_url,
    update_url,
    delete_url,
    get_url_stats,
    search_urls,
    cleanup_unused_links,
    get_expired_urls_history,
)
from src.app.core.config import settings

router = APIRouter()


@router.post("/shorten", response_model=URL, status_code=status.HTTP_201_CREATED)
def create_link(
    url: URLCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Create a shortened URL.

    Requires authentication.
    """
    try:
        return create_short_url(db, url, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/search", response_model=list[URL])
def search_links(
    original_url: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Search for URLs by original URL with pagination.

    Does not require authentication.
    """
    return search_urls(db, original_url, limit, offset)


@router.get("/expired-history", response_model=list[URL])
def get_expired_links_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Get history of expired links.

    This endpoint returns a list of URLs that have expired,
    ordered by expiration date (most recent first).

    Requires authentication.
    """
    return get_expired_urls_history(db, limit, offset)


@router.post("/cleanup-unused", status_code=status.HTTP_200_OK)
def cleanup_unused_links_endpoint(
    days: int = Query(settings.DEFAULT_EXPIRY_DAYS, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Delete URLs that haven't been used for the specified number of days.

    Requires authentication.
    """
    deleted_count = cleanup_unused_links(db, days)
    return {"message": f"Deleted {deleted_count} unused links"}


@router.get("/{short_code}/stats", response_model=URLStats)
def get_link_stats(
    short_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Get statistics for a shortened URL.

    Requires authentication.
    """
    url = get_url_stats(db, short_code)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )
    return url


@router.put("/{short_code}", response_model=URL)
def update_link(
    short_code: str,
    url_update: URLUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Update a shortened URL.

    Requires authentication.
    """
    url = update_url(db, short_code, url_update)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )
    return url


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Delete a shortened URL.

    Requires authentication.
    """
    if not delete_url(db, short_code):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )
