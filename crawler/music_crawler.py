# ✅ crawler/music_crawler.py

import requests, os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from utils.db_utils import save_to_db
from utils.emotion_utils import extract_emotion_tags, infer_emotion_with_model, filter_valid_emotions
from utils.emotion_keywords import emotion_keywords

load_dotenv()

def run():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("🚫 YouTube API 키 없음")
        return

    # 감정별 키워드를 리스트로 통합
    keywords = []
    for kw_list in emotion_keywords.values():
        keywords.extend(kw_list)

    data = []
    for keyword in keywords:
        print(f"\n🔍 키워드: {keyword}")
        for page_token in range(1, 5):  # 최대 4페이지
            start_index = (page_token - 1) * 5
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={keyword}&key={api_key}&type=video&maxResults=5&startIndex={start_index}"
            try:
                res = requests.get(url)
                if res.status_code == 403 or "error" in res.json():
                    print("🚫 YouTube API 한도 초과 또는 오류 발생")
                    return

                results = res.json().get("items", [])
                if not results:
                    break

                for item in results:
                    title = item["snippet"]["title"]
                    description = item["snippet"].get("description", "")
                    text = f"{title} {description}"
                    video_url = f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                    thumbnail_url = item["snippet"]["thumbnails"]["high"]["url"]

                    # 감정 추출
                    emotion = extract_emotion_tags(text)
                    if not emotion:
                        emotion = infer_emotion_with_model(text)
                    emotion = filter_valid_emotions(emotion)
                    if not emotion:
                        print(f"🚫 감정 없음 → 저장 생략: {title}")
                        continue

                    content = {
                        "title": title,
                        "url": video_url,
                        "emotion_tags": emotion,
                        "thumbnail_url": thumbnail_url
                    }
                    print(f"🎵 크롤링 결과: {content}")
                    data.append(content)

            except Exception as e:
                print("❌ 유튜브 크롤링 실패:", e)
                continue

    print(f"\n📦 DB 저장 시도 음악 수: {len(data)}")
    save_to_db("music", data)

if __name__ == "__main__":
    run()

