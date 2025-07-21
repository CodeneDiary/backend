# ✅ utils/db_utils.py

import sqlite3
import os
import json

def get_connection():
    return sqlite3.connect("data/emotion.db")

# DB 저장 함수
def save_to_db(table, items):
    conn = get_connection()
    cur = conn.cursor()
    saved_count = 0
    for item in items:
        cur.execute(f"SELECT id FROM {table} WHERE title = ?", (item['title'],))
        if cur.fetchone():
            print(f"🔁 이미 존재함: {item['title']}")
            continue
        # 컬럼 유무에 따라 삽입 쿼리 다르게
        if 'thumbnail_url' in item:
            cur.execute(
                f"INSERT INTO {table} (title, url, emotion_tags, thumbnail_url) VALUES (?, ?, ?, ?)",
                (item['title'], item['url'], ','.join(item['emotion_tags']), item['thumbnail_url'])
            )
        elif 'poster_url' in item:
            cur.execute(
                f"INSERT INTO {table} (title, url, emotion_tags, poster_url) VALUES (?, ?, ?, ?)",
                (item['title'], item['url'], ','.join(item['emotion_tags']), item['poster_url'])
            )
        else:
            cur.execute(
                f"INSERT INTO {table} (title, url, emotion_tags) VALUES (?, ?, ?)",
                (item['title'], item['url'], ','.join(item['emotion_tags']))
            )

        print(f"✅ 저장 완료: {item['title']}")
        saved_count += 1

    conn.commit()
    conn.close()
    print(f"\n✅ 총 저장된 항목 수: {saved_count}")

# 모든 콘텐츠 로드 (optional)
def load_all_content():
    conn = get_connection()
    cur = conn.cursor()
    all_items = []

    for table in ["books", "movies", "music", "quotes"]:
        if table == "movies":
            cur.execute(f"SELECT title, url, emotion_tags, poster_url FROM {table}")
            rows = cur.fetchall()
            for title, url, tags, poster in rows:
                all_items.append({
                    "title": title,
                    "url": url,
                    "emotion_tags": tags.split(","),
                    "poster_url": poster
                })

        elif table == "music":
            cur.execute(f"SELECT title, url, emotion_tags, thumbnail_url FROM {table}")
            rows = cur.fetchall()
            for title, url, tags, thumb in rows:
                all_items.append({
                    "title": title,
                    "url": url,
                    "emotion_tags": tags.split(","),
                    "thumbnail_url": thumb
                })

        elif table == "books":
            cur.execute(f"SELECT title, url, emotion_tags, thumbnail_url FROM {table}")
            rows = cur.fetchall()
            for title, url, tags, thumb in rows:
                all_items.append({
                    "title": title,
                    "url": url,
                    "emotion_tags": tags.split(","),
                    "thumbnail_url": thumb
                })

        else:  # quotes (썸네일 없음)
            cur.execute(f"SELECT title, url, emotion_tags FROM {table}")
            rows = cur.fetchall()
            for title, url, tags in rows:
                all_items.append({
                    "title": title,
                    "url": url,
                    "emotion_tags": tags.split(",")
                })

    conn.close()
    return all_items

def save_to_json(file_path, items):
    """
    데이터를 JSON 파일로 저장합니다.

    Parameters
    ----------
    file_path : str
        저장할 JSON 파일 경로
    items : list or dict
        저장할 데이터 (보통 list[dict] 형태)
    """
    # 디렉토리가 없다면 생성
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # JSON 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=4)

    print(f"✅ JSON 저장 완료: {file_path}")

