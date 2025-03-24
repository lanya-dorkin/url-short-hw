from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from src.app.db.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    urls = relationship("URL", back_populates="user", cascade="all, delete-orphan")
