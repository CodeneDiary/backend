import sqlite3

# DB 연결
conn = sqlite3.connect("emotion.db")
cursor = conn.cursor()

# 예시 데이터
books = [
    ("미움 받을 용기", "https://www.yes24.com/Product/Goods/12627433", "감사,희망"),
    ("내가 너의 첫사랑이 아니어도", "https://www.yes24.com/Product/Goods/107088952", "설렘,사랑"),
    ("사랑할 때 알아야 할 것들", "https://www.yes24.com/Product/Goods/63898324", "설렘,희망"),
    ("죽고 싶지만 떡볶이는 먹고 싶어", "https://www.yes24.com/Product/Goods/64581273", "우울,외로움"),
    ("혼자가 혼자에게", "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=265901280", "외로움,우울"),
]

movies = [
    ("월터의 상상은 현실이 된다", "https://www.netflix.com/title/70293622", "감사,희망,기대"),
    ("인사이드 아웃", "https://www.disneyplus.com/movies/inside-out", "감사,공감,사랑"),
    ("어바웃 타임", "https://www.netflix.com/title/70265153", "설렘,사랑,희망"),
    ("라라랜드", "https://www.netflix.com/title/80095365", "설렘,신남"),
    ("너의 이름은", "https://www.watcha.com/contents/mdYyzKD", "설렘,그리움"),
    ("바닷마을 다이어리", "https://www.watcha.com/contents/m5R4KeX", "외로움,희망,우울"),
    ("이터널 선샤인", "https://www.netflix.com/title/60034550", "우울,상실,외로움"),
]

music = [
    ("김동률 – 감사", "https://www.youtube.com/watch?v=V09ENoBfRr8", "감사,편안,사랑"),
    ("나얼 – 같은 시간 속의 너", "https://www.youtube.com/watch?v=AfV-SlMdu7A", "감사,그리움"),
    ("방탄소년단 – Dynamite", "https://www.youtube.com/watch?v=gdZLi9oWNZg", "신남,기쁨"),
    ("NewJeans – Super Shy", "https://www.youtube.com/watch?v=ArmDp-zijuc", "설렘,기쁨"),
    ("아이유 – 마음", "https://www.youtube.com/watch?v=0-q1KafFCLU", "우울,외로움"),
    ("정승환 – 눈사람", "https://www.youtube.com/watch?v=c3Vjx0rPs_o", "우울,상실,외로움"),
]

quotes = [
    ("당신이 지금 가진 모든 것이, 한때 당신이 바라던 것이었다. - 익명", "", "감사"),
    ("고맙다는 말은 짧지만, 마음을 전하는 가장 따뜻한 언어입니다. - 익명", "", "감사"),
    ("모든 시작이 설레는 이유는 가능성이 가득하기 때문이다. - 익명", "", "설렘,희망"),
    ("뛰는 심장이 말해줘. 지금 이 순간을 즐겨! - 익명", "", "신남,기대"),
    ("혼자인 날에도 나를 안아줄 수 있기를. - 익명", "", "외로움"),
    ("깊은 밤이 지나면 반드시 아침이 옵니다. - 익명", "", "우울"),
]

# INSERT 실행
cursor.executemany("INSERT INTO books (title, url, emotion_tags) VALUES (?, ?, ?)", books)
cursor.executemany("INSERT INTO movies (title, url, emotion_tags) VALUES (?, ?, ?)", movies)
cursor.executemany("INSERT INTO music (title, url, emotion_tags) VALUES (?, ?, ?)", music)
cursor.executemany("INSERT INTO quotes (title, url, emotion_tags) VALUES (?, ?, ?)", quotes)

# 저장 및 종료
conn.commit()
conn.close()
