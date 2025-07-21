import sqlite3
import random

# 주요 감정별 추천 콘텐츠 감정군 (라벨맵 내 긍정 감정만 엄선)
emotion_groups = {
    "기쁨": ["기쁨", "신남", "희열", "쾌감", "설렘", "편안", "후련함", "감사", "사랑", "공감", "기대"],
    "평온": ["편안", "후련함", "공감", "기대"],
    "슬픔": ["희망", "공감", "감사", "사랑", "편안", "후련함"],
    "분노": ["편안", "후련함", "공감", "사랑"],
    "불안": ["편안", "공감", "희망", "사랑"],
    "무감정": ["흥미", "신남", "기대", "설렘", "쾌감"]
}

# DB 경로
DB_PATH = "data/emotion.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def recommend_content(user_emotion):
    if user_emotion not in emotion_groups:
        return {"error": f"지원하지 않는 감정입니다: {user_emotion}"}

    target_emotions = emotion_groups[user_emotion]

    conn = get_connection()
    cur = conn.cursor()

    results = {}

    # 테이블별 이미지 필드 매핑
    table_image_field = {
        "books": "thumbnail_url",
        "movies": "poster_url",
        "music": "thumbnail_url",
        "quotes": None
    }

    # 테이블별 추천 쿼리
    for table, img_field in table_image_field.items():
        # 감정태그 조건문 만들기 (LIKE 문 여러개 OR 결합)
        like_clauses = " OR ".join(
            [f"emotion_tags LIKE '%{emotion}%'" for emotion in target_emotions]
        )
        query = f"""
            SELECT title, url {', ' + img_field if img_field else ''} FROM {table}
            WHERE {like_clauses}
            ORDER BY RANDOM()
            LIMIT 1
        """
        cur.execute(query)
        row = cur.fetchone()
        if row:
            content = {
                "title": row[0],
                "url": row[1],
            }
            if img_field:
                content["image_url"] = row[2]
            results[table] = content
        else:
            results[table] = None

    conn.close()
    return results
