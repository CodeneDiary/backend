# app/main.py

from fastapi import FastAPI, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.emotion import predict_emotion
from app import model, database, recommender
from app.chatbot import router as chatbot_router
from app.recommender import get_recommendations
from app.utils import get_current_user
from app.firebase_auth import verify_firebase_token, get_current_user_id
from datetime import datetime, date
from app.deps import get_db
from dotenv import load_dotenv
from typing import Optional, List
from fastapi.responses import JSONResponse
import os

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

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

# 일기 목록 반환
@app.get("/diary/list")
def get_diaries(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return db.query(model.Diary).filter(model.Diary.user_id == user_id).all()


class DiaryUpdateRequest(BaseModel):
    text: str
    emotion: str

@app.put("/diary/by-date/{date}")
def update_diary_by_date(
    date: date,
    update: DiaryUpdateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    # 사용자 + 날짜 기준으로 해당 일기 찾기
    diary = db.query(model.Diary).filter(
        model.Diary.user_id == user_id,
        model.Diary.date == date
    ).first()

    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")

    # 내용과 감정 모두 업데이트
    diary.content = update.text
    diary.emotion = update.emotion
    db.commit()

    return {
        "message": "Diary updated",
        "id": diary.id,
        "date": diary.date,
        "content": diary.content,
        "emotion": diary.emotion
    }

@app.get("/diary/by-date/{date}")
def get_diary_by_date(
    date: date,  #  문자열을 날짜로 파싱
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    diary = db.query(model.Diary).filter(
        model.Diary.user_id == user_id,
        model.Diary.date == date  # 날짜 컬럼으로 조회
    ).first()

    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")

    return {
        "id": diary.id,
        "content": diary.content,
        "emotion": diary.emotion,
        "confidence": diary.confidence,
        "date": diary.date,
        "created_at": diary.created_at
    }

# 기존 감정 분석만 반환하는 API
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


@app.get("/my-info")
def my_info(user_email: str = Depends(verify_firebase_token)):
    return {"email": user_email}

class Recommendation(BaseModel):
    title: str
    url: str
    emotion_tags: str
    image: Optional[str] = None

class RecommendationResponse(BaseModel):
    emotion: str
    books: List[Recommendation]
    movies: List[Recommendation]
    music: List[Recommendation]
    quotes: List[Recommendation]

@app.post("/recommend/from-emotion", response_model=RecommendationResponse)
def recommend_from_emotion(
    emotion: str = Query(..., description="기반 감정 (예: 행복, 슬픔 등)")
):
    try:
        return {
            "emotion": emotion,
            "books": get_recommendations("books", emotion, RECOMMEND_DB_PATH),
            "movies": get_recommendations("movies", emotion, RECOMMEND_DB_PATH),
            "music": get_recommendations("music", emotion, RECOMMEND_DB_PATH),
            "quotes": get_recommendations("quotes", emotion, RECOMMEND_DB_PATH)
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/diary/{diary_id}")
def delete_diary(
    diary_id: int = Path(..., description="삭제할 일기의 ID"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    diary = db.query(model.Diary).filter(
        model.Diary.id == diary_id,
        model.Diary.user_id == user_id  # 본인 글만 삭제 가능
    ).first()

    if not diary:
        raise HTTPException(status_code=404, detail="일기를 찾을 수 없습니다.")

    db.delete(diary)
    db.commit()

    return {"message": f"{diary_id}번 일기가 삭제되었습니다."}

@app.get("/diary/search")
def search_diaries(
    keyword: str = Query(..., min_length=1, description="검색할 키워드"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    diaries = db.query(model.Diary).filter(
        model.Diary.user_id == user_id,
        model.Diary.content.ilike(f"%{keyword}%")
    ).all()

    return diaries