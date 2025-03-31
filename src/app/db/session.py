from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from src.app.core.config import settings
from src.app.db.base import Base

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def get_db() -> Generator:
    if SessionLocal is None:
        raise RuntimeError(
            "Database session not initialized. Make sure you're not in test mode."
        )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
