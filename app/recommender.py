from fastapi import APIRouter, Query
import sqlite3
import os

DB_PATH = os.path.join("app", "emotion.db")
router = APIRouter()

def get_recommendations(content_type, emotion, db_path):
    """emotion.db에서 콘텐츠 종류와 감정 기반 추천 항목 반환"""
    """emotion이 있을 경우 감정 기반 추천, 없으면 인기(무작위) 추천"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if emotion:
        query = f"""
            SELECT title, url
            FROM {content_type}
            WHERE emotion_tags LIKE ?
            LIMIT 5;
            """
        cursor.execute(query, (f"%{emotion}%",))
    else:
        query = f"""
            SELECT title, url
            FROM {content_type}
            ORDER BY RANDOM()
            LIMIT 5;
            """
        cursor.execute(query)

    results = cursor.fetchall()
    conn.close()

    return [{"title": row[0], "url": row[1]} for row in results]

# 추천 API 엔드포인트
@router.get("/recommend")
def recommend_all(
    emotion: str = Query(..., description="감정 키워드 (예: 우울, 설렘 등)")
):
    try:
        return {
            "emotion": emotion or "default",
            "books": get_recommendations("books", emotion, DB_PATH),
            "movies": get_recommendations("movies", emotion, DB_PATH),
            "music": get_recommendations("music", emotion, DB_PATH),
            "quotes": get_recommendations("quotes", emotion, DB_PATH)
        }
    except Exception as e:
        return {"error": str(e)}