# app/firebase_auth.py
import firebase_admin
from firebase_admin import credentials, auth, initialize_app
from fastapi import Request, HTTPException, Depends, Header
import os
import json

# Firebase 인증 초기화 (환경변수에 파일 경로가 들어 있음)
firebase_path = os.path.join(os.path.dirname(__file__), os.getenv("FIREBASE_CREDENTIALS"))
if not firebase_path:
    raise RuntimeError("FIREBASE_CREDENTIALS 환경변수가 비어 있습니다")

with open(firebase_path, "r") as f:
    firebase_json_dict = json.load(f)

cred = credentials.Certificate(firebase_json_dict)

# 중복 초기화 방지
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)


# 요청에서 Firebase 토큰을 꺼내 UID 반환
def verify_firebase_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No auth token provided")

    id_token = auth_header.split(" ")[1]

    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# FastAPI Depends용 사용자 UID 추출기
async def get_current_user_id(authorization: str = Header(...)):
    try:
        # "Bearer <id_token>" 형식에서 토큰만 추출
        id_token = authorization.split(" ")[1]
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token")