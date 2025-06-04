import sqlite3
import os

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
