# app/models.py

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="default_user")  # 추후 로그인 연동 고려
    content = Column(String)
    emotion = Column(String)
    confidence = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
