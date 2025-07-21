# ✅ crawler/book_crawler.py

import requests
import os
from dotenv import load_dotenv
from utils.db_utils import save_to_db
from utils.emotion_utils import extract_emotion_tags, infer_emotion_with_model, filter_valid_emotions

load_dotenv()

def run():
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ Naver API 키 누락")
        return

    # 감정 기반 키워드 (원하는 대로 확장 가능)
    keywords = [
        "위로 고전",  # 슬픔
        "유쾌한 고전",  # 기쁨
        "마음이 편안해지는 소설",     # 불안
        "감정 조절 고전",     # 분노
        "평온한 유명고전",      # 평온
        "우울 위로 고전",   # 무감정/우울
    ]

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    data = []

    for keyword in keywords:
        print(f"\n🔍 키워드: {keyword}")
        url = f"https://openapi.naver.com/v1/search/book.json?query={keyword}&display=10"
        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            books = res.json().get("items", [])

            for book in books:
                title = book["title"].replace("<b>", "").replace("</b>", "").strip()
                url = book["link"]
                thumbnail_url = book["image"]
                text = f"{title} {book['description']}"

                emotion = extract_emotion_tags(text)
                if not emotion:
                    emotion = infer_emotion_with_model(text)

                emotion = filter_valid_emotions(emotion)
                if not emotion:
                    print(f"🚫 감정 없음 → 저장 생략: {title}")
                    continue

                content = {
                    "title": title,
                    "url": url,
                    "emotion_tags": emotion,
                    "thumbnail_url": thumbnail_url
                }
                print(f"📚 크롤링 결과: {content}")
                data.append(content)

        except Exception as e:
            print(f"❌ 네이버 API 요청 실패: {e}")
            continue

    print(f"\n📦 DB 저장 시도 책 수: {len(data)}")
    save_to_db("books", data)

if __name__ == "__main__":
    run()


