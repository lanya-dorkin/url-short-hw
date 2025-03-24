from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.app.api.deps import get_db, get_current_active_user
from src.app.schemas.url import URL, URLCreate, URLUpdate, URLStats
from src.app.services.url_service import (
    create_short_url,
    get_url_by_short_code,
    update_url,
    delete_url,
    increment_visits,
    get_url_stats,
    search_urls,
)

router = APIRouter()


@router.post("/shorten", response_model=URL, status_code=status.HTTP_201_CREATED)
def create_link(
    url: URLCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    try:
        return create_short_url(db, url, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/search", response_model=list[URL])
def search_links(
    original_url: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return search_urls(db, original_url)


@router.get("/{short_code}")
def get_link(short_code: str, db: Session = Depends(get_db)):
    url = get_url_by_short_code(db, short_code)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )

    increment_visits(db, short_code)

    return RedirectResponse(url.original_url)


@router.get("/{short_code}/stats", response_model=URLStats)
def get_link_stats(
    short_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
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
    if not delete_url(db, short_code):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )
