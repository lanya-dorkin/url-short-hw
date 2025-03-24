from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.app.api.v1.endpoints import users, links
from src.app.api.deps import get_db
from src.app.services.url_service import get_url_by_short_code, increment_visits

app = FastAPI(
    title="Yet another URL Shortener API",
    description="A FastAPI-based URL shortening service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(links.router, prefix="/api/v1/links", tags=["links"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to URL Shortener API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/{short_code}")
async def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    """
    Redirect to the original URL associated with the given short code.
    Supports both GET and HEAD methods.
    """
    url = get_url_by_short_code(db, short_code)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )

    increment_visits(db, short_code)

    return RedirectResponse(url.original_url)
