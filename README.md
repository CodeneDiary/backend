## ⚙️ 환경 세팅 & 실행 방법

### 1. 사전 준비
```
git clone https://github.com/CodeneDiary/backend.git
cd backend
```
### 2. 라이브러리 설치
```
pip install -r requirements.txt
```
### 3. 서버 실행
```
uvicorn app.main:app --reload
```
## 📂 폴더 구조
```
backend
├── app/
│   ├── chatbot.py         # 대화 흐름 제어
│   ├── database.py        # DB 연결 설정
│   ├── deps.py            # FastAPI 의존성
│   ├── emotion.py         # 감정 모드 분류기
│   ├── firebase_auth.py   # Firebase 인증 유틸
│   ├── main.py            # FastAPI 진입점
│   ├── model.py           # SQLAlchemy 모델 정의
│   ├── recommender.py     # 추천 API 엔드포인트
│   └── utils.py           # 유틸 함수
├── data/
│   ├── emotion.db         # 감정 사전 DB
│   └── insert_data.py     # DB 초기화 스크립트
├── recommendation/
│   └── recommender.py     # 사주 기반 직업 추천 로직
├── diary.db               # 메인 DB (일기 및 대화 기록)
├── .gitignore
├── requirements.txt
└── README.md
```
