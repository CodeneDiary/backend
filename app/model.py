# app/models.py

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship

class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Firebase UID
    content = Column(String)
    emotion = Column(String)
    confidence = Column(String)
    date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    conversations = relationship("ConversationLog", back_populates="diary", cascade="all, delete-orphan") #

#대화 내역 테이블 추가
class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, index=True)
    diary_id = Column(Integer, ForeignKey("diaries.id"), index=True)
    user_input = Column(Text)
    response = Column(Text)
    mode = Column(String(1))  # 'T' or 'F'
    audio_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    diary = relationship("Diary", back_populates="conversations")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, index=True)  # Firebase UID
    email = Column(String, unique=True, index=True)  # 사용자 이메일
    name = Column(String, nullable=True)  # (선택) 사용자 이름
