# app/models.py

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Firebase UID
    content = Column(String)
    emotion = Column(String)
    confidence = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, index=True)  # Firebase UID
    email = Column(String, unique=True, index=True)  # 사용자 이메일
    name = Column(String, nullable=True)  # (선택) 사용자 이름
