# ✅ crawler/movie_crawler.py

import requests
import os
from dotenv import load_dotenv
from utils.db_utils import save_to_db
from utils.emotion_utils import extract_emotion_tags, infer_emotion_with_model, filter_valid_emotions

load_dotenv()

POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

def run():
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        print("🚫 TMDB API 키 없음")
        return

    api_endpoints = [
        "popular",
        "top_rated",
        "now_playing",
        "upcoming"
    ]

    all_data = []

    try:
        for endpoint in api_endpoints:
            for page in range(1, 3):  # 각 카테고리 1~2페이지 크롤링
                url = f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={api_key}&language=ko-KR&page={page}"
                response = requests.get(url)
                results = response.json().get("results", [])
                print(f"\n📡 TMDB {endpoint} 영화 {page}페이지에서 가져온 영화 수: {len(results)}")

                for movie in results:
                    title = movie.get("title", "")
                    overview = movie.get("overview", "")
                    poster_path = movie.get("poster_path", "")
                    text = f"{title} {overview}"

                    emotion = extract_emotion_tags(text)
                    if not emotion:
                        emotion = infer_emotion_with_model(text)

                    emotion = filter_valid_emotions(emotion)

                    if not emotion:
                        print(f"🚫 감정 없음 → 저장 생략: {title}")
                        continue

                    poster_url = POSTER_BASE_URL + poster_path if poster_path else ""

                    item = {
                        "title": title,
                        "url": f"https://www.themoviedb.org/movie/{movie.get('id')}",
                        "emotion_tags": emotion,
                        "poster_url": poster_url
                    }
                    print(f"📝 크롤링 결과: {item}")
                    all_data.append(item)

        print(f"\n📦 DB 저장 시도 영화 수: {len(all_data)}")
        save_to_db("movies", all_data)

    except Exception as e:
        print("❌ 영화 크롤링 실패:", e)

if __name__ == "__main__":
    run()


