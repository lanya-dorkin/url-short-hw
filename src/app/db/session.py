from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
import sys
from src.app.core.config import settings
from src.app.db.base import Base

# Only create engine and create tables if not in test mode
is_test = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)

if not is_test:
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
else:
    engine = None
    SessionLocal = None


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
