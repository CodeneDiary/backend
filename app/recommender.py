from fastapi import APIRouter, Query
import sqlite3
import os

DB_PATH = os.path.join("app", "emotion.db")
router = APIRouter()

def get_recommendations(content_type, emotion, db_path):
    """emotion.db에서 콘텐츠 종류와 감정 기반 추천 항목 반환"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f"""
    SELECT title, url
    FROM {content_type}
    WHERE emotion_tags LIKE ?
    LIMIT 5;
    """
    cursor.execute(query, (f"%{emotion}%",))
    results = cursor.fetchall()
    conn.close()

    return [{"title": row[0], "url": row[1]} for row in results]

# 추천 API 엔드포인트
@router.get("/recommend")
def recommend(
    content_type: str = Query(..., description="books | movies | music | quotes"),
    emotion: str = Query(..., description="감정 키워드 (예: 우울, 설렘 등)")
):
    try:
        results = get_recommendations(content_type, emotion, DB_PATH)
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}