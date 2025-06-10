# app/firebase_auth.py
import firebase_admin
from firebase_admin import credentials, auth, initialize_app
from fastapi import Request, HTTPException, Depends, Header
import os
import json

# Firebase 인증 초기화 (환경변수에 파일 경로가 들어 있음)
# JSON 문자열을 읽어 dict로 파싱
firebase_cred_str = os.getenv("FIREBASE_CREDENTIALS")
firebase_cred_dict = json.loads(firebase_cred_str)

# Firebase 초기화
cred = credentials.Certificate(firebase_cred_dict)
initialize_app(cred)


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