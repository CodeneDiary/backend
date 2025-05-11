# app/main.py

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.emotion import predict_emotion
from app import model, database

# FastAPI 앱 객체 생성
app = FastAPI()

# DB 테이블 생성
model.Base.metadata.create_all(bind=database.engine)


# Pydantic 스키마
class TextInput(BaseModel):
    text: str


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
def analyze_and_save(input: TextInput, db: Session = Depends(get_db)):
    result = predict_emotion(input.text)

    diary = model.Diary(
        content=input.text,
        emotion=result["label"],
        confidence=str(result["confidence"])
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
            "confidence": diary.confidence
        }
    }


# 일기 목록 반환
@app.get("/diary/list")
def get_diaries(db: Session = Depends(get_db)):
    return db.query(model.Diary).all()

