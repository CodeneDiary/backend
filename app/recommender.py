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
        select_fields = "title, url, emotion_tags"
        image_index = None  # 이미지 없음
    elif content_type == "books":
        select_fields = "title, url, emotion_tags, thumbnail_url"
        image_index = 3
    elif content_type == "music":
        select_fields = "title, url, emotion_tags, thumbnail_url"
        image_index = 3
    elif content_type == "movies":
        select_fields = "title, url, emotion_tags, poster_url"
        image_index = 3
    else:
        return []

    if emotion:
        query = f"""
                SELECT {select_fields}
                FROM {content_type}
                WHERE emotion_tags LIKE ?
                ORDER BY id DESC
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
            "url": row[1],
            "emotion_tags": row[2],
        }
        if image_index is not None:
            content["image"] = row[image_index]
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