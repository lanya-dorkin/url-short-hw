from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import os

from src.app.api.v1.endpoints import users, links
from src.app.api.deps import get_db
from src.app.services.url_service import get_url_by_short_code, increment_visits
from src.app.core.config import settings, logger

app = FastAPI(
    title="Yet Another URL Shortener API",
    description="""
    A FastAPI-based URL shortening service.
    
    ## Features
    * Create custom short links
    * Track link usage statistics
    * Set expiration dates for links
    * Search for links
    
    ## Documentation
    * Swagger UI: [/docs](/docs)
    * ReDoc: [/redoc](/redoc)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
    contact={
        "name": "danya",
        "email": "danya.lorkin@gmail.com",
    },
    license_info={
        "name": "MIT",
    },
)

# Get allowed origins from environment variable or use default
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(links.router, prefix="/api/v1/links", tags=["links"])


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to URL Shortener API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/{short_code}", tags=["redirect"])
async def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    url = get_url_by_short_code(db, short_code)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found"
        )

    increment_visits(db, short_code)

    return RedirectResponse(url.original_url)
