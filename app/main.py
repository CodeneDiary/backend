# app/main.py

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.emotion import predict_emotion
from app import model, database
from app.chatbot import router as chatbot_router
from app.utils import get_current_user
from app.firebase_auth import verify_firebase_token, get_current_user_id
from datetime import datetime

# FastAPI 앱 객체 생성
app = FastAPI()

# DB 테이블 생성
model.Base.metadata.create_all(bind=database.engine)
app.include_router(chatbot_router)

# Pydantic 스키마
class TextInput(BaseModel):
    text: str
    date: str


# DB 세션 연결 함수
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 기존 감정 분석만 반환하는 API (기존 코드 유지!)
@app.post("/analyze/emotion")
def analyze_emotion(input: TextInput):
    result = predict_emotion(input.text)
    return result


# 감정 분석 + DB 저장
@app.post("/diary/text")
def analyze_and_save(
        input: TextInput,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user_id)
):
    try:
        result = predict_emotion(input.text)

        parsed_date = datetime.strptime(input.date, "%Y-%m-%d").date()

        diary = model.Diary(
            user_id=user_id,
            content=input.text,
            emotion=result[0]["label"],
            confidence=str(result[0]["confidence"]),
            date=parsed_date
        )
        db.add(diary)
        db.commit()
        db.refresh(diary)

        return {
            "message": "저장 완료!",
            "diary": {
                "id": diary.id,
                "content": diary.content,
                "emotion": diary.emotion,
                "confidence": diary.confidence,
                "date": diary.date
            }
        }
    except Exception as e:
        print("🔥 서버 오류:", e)
        raise HTTPException(status_code=500, detail="서버 내부 오류")


# 일기 목록 반환
@app.get("/diary/list")
def get_diaries(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return db.query(model.Diary).filter(model.Diary.user_id == user_id).all()


@app.get("/my-info")
def my_info(user_email: str = Depends(verify_firebase_token)):
    return {"email": user_email}
