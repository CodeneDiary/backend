# app/firebase_auth.py
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Request, HTTPException, Depends, Header
import os
import json

# 최초 1회만 초기화
firebase_json_str = os.getenv("FIREBASE_CREDENTIALS")
firebase_json_dict = json.loads(firebase_json_str)
cred = credentials.Certificate(firebase_json_dict)
firebase_admin.initialize_app(cred)

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

async def get_current_user_id(authorization: str = Header(...)):
    try:
        # "Bearer <id_token>" 형식에서 토큰만 추출
        id_token = authorization.split(" ")[1]
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token")