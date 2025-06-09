# app/main.py

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.emotion import predict_emotion
from app import model, database, recommender
from app.chatbot import router as chatbot_router
from app.recommender import get_recommendations
from app.utils import get_current_user
from app.firebase_auth import verify_firebase_token, get_current_user_id
from datetime import datetime
from app.deps import get_db
from dotenv import load_dotenv
import os

load_dotenv()

# FastAPI 앱 객체 생성
app = FastAPI()

# DB 테이블 생성
model.Base.metadata.create_all(bind=database.engine)
app.include_router(chatbot_router)
app.include_router(recommender.router, prefix="/api")

# 추천용 DB 경로
RECOMMEND_DB_PATH = os.path.join("data", "emotion.db")

# Pydantic 스키마
class TextInput(BaseModel):
    text: str
    date: str


# # DB 세션 연결 함수
# def get_db():
#     db = database.SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


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

@app.post("/recommend/from-text")
def recommend_from_text(
    text: str = Query(..., description="사용자 입력 텍스트"),
    content_type: str = Query(..., description="books | movies | music | quotes")
):
    try:
        # 1. 감정 분석
        emotions = predict_emotion(text)
        top_emotion = emotions[0]["label"]  # confidence 가장 높은 감정 사용

        # 2. 감정 기반 추천
        results = get_recommendations(content_type, top_emotion, RECOMMEND_DB_PATH)

        return {
            "emotion": top_emotion,
            "results": results
        }

    except Exception as e:
        return {"error": str(e)}