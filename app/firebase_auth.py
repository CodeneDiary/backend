# app/firebase_auth.py
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Request, HTTPException
import os

# 최초 1회만 초기화
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(BASE_DIR, "firebase_admin.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

def verify_firebase_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No auth token provided")

    id_token = auth_header.split(" ")[1]

    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token["email"]  # 또는 uid
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
