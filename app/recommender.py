from fastapi import APIRouter, Query
import sqlite3
import os
from typing import List, Optional

DB_PATH = os.path.join("app", "emotion.db")
router = APIRouter()

def get_recommendations(content_type, emotion, db_path):
    """emotion.db에서 콘텐츠 종류와 감정 기반 추천 항목 반환"""
    """emotion이 있을 경우 감정 기반 추천, 없으면 인기(무작위) 추천"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if content_type == "quotes":
        select_fields = "title, url"
    elif content_type in ["books", "music"]:
        select_fields = "title, url, thumbnail_url"
    elif content_type == "movies":
        select_fields = "title, url, poster_url"
    else:
        return []

    if emotion:
        query = f"""
            SELECT {select_fields}
            FROM {content_type}
            WHERE emotion_tags LIKE ?
            LIMIT 5;
        """
        cursor.execute(query, (f"%{emotion}%",))
    else:
        query = f"""
            SELECT {select_fields}
            FROM {content_type}
            ORDER BY RANDOM()
            LIMIT 5;
        """
        cursor.execute(query)

    results = cursor.fetchall()
    conn.close()

    # 결과 포맷 정리
    content_list = []
    for row in results:
        content = {
            "title": row[0],
            "url": row[1]
        }
        if len(row) == 3:  # 썸네일 또는 포스터가 있을 경우
            content["image"] = row[2]
        content_list.append(content)

    return content_list

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