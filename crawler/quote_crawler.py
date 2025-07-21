# ✅ crawler/quotes_crawler.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from tqdm import tqdm
from dotenv import load_dotenv
from utils.emotion_utils import infer_emotion_with_model
from utils.db_utils import save_to_db

# ✅ 번역 관련/
load_dotenv()
GOOGLE_API_KEY = os.getenv("YOUTUBE_API_KEY")
TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"

def translate_text(text, target="ko"):
    try:
        params = {
            "q": text,
            "target": target,
            "format": "text",
            "key": GOOGLE_API_KEY
        }
        response = requests.post(TRANSLATE_URL, params=params)
        response.raise_for_status()
        return response.json()["data"]["translations"][0]["translatedText"]
    except Exception as e:
        print(f"[번역 실패] {text[:30]}... → {e}")
        return text  # 번역 실패 시 원문 반환

# ✅ 명언 전체 크롤링 함수
def crawl_all_quotes():
    base_url = "https://quotes.toscrape.com/page/{}/"
    all_quotes = []

    for page in range(1, 11):  # 총 10페이지
        res = requests.get(base_url.format(page))
        soup = BeautifulSoup(res.text, "html.parser")
        quotes = soup.select(".quote")

        if not quotes:
            break

        for quote in quotes:
            text = quote.select_one(".text").get_text(strip=True).strip("“”")
            author = quote.select_one(".author").get_text(strip=True)

            translated = translate_text(text)
            emotions = infer_emotion_with_model(translated)

            all_quotes.append({
                "text": text,
                "author": author,
                "translated": translated,
                "emotions": emotions
            })

    return all_quotes

# ✅ JSON 저장
def save_to_json(data, filepath="data/quotes.json"):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ✅ 메인 실행
if __name__ == "__main__":
    print("📌 명언 전체 크롤링 중...")
    quotes = crawl_all_quotes()
    print(f"✅ 총 {len(quotes)}개 크롤링 완료")

    save_to_json(quotes)
   
    # 전처리: 'translated' 키를 'title'로 바꾸고 url은 빈 문자열로 세팅
    quotes_for_db = []
    for item in quotes:
        quotes_for_db.append({
            "title": item["translated"],
            "url": "",
            "emotion_tags": item["emotions"]
        })

    save_to_db("quotes", quotes_for_db)
    print("✅ JSON 및 DB 저장 완료")




