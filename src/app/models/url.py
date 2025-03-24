from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.app.db.base import BaseModel

class URL(BaseModel):
    __tablename__ = "urls"
    
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    visits = Column(Integer, default=0)
    last_visited_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    user = relationship("User", back_populates="urls") 