# app/auth_kakao.py

from fastapi import APIRouter, Request, HTTPException
import httpx, os
from app.utils import create_access_token
from app import model, database

router = APIRouter()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

@router.get("/auth/kakao/callback")
async def kakao_callback(code: str):
    # 1. 토큰 요청
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=token_data)
        token_json = token_res.json()
        access_token = token_json.get("access_token")

        # 2. 사용자 정보 요청
        user_res = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_res.json()

        kakao_email = user_info.get("kakao_account", {}).get("email")
        if not kakao_email:
            raise HTTPException(status_code=400, detail="카카오 이메일 접근 권한 없음")

        # 3. DB에 사용자 등록 or 조회
        db = database.SessionLocal()
        user = db.query(model.User).filter(model.User.email == kakao_email).first()
        if not user:
            user = model.User(email=kakao_email, hashed_password="kakao-oauth")
            db.add(user)
            db.commit()

        # 4. JWT 발급
        jwt_token = create_access_token({"sub": kakao_email})
        return {"access_token": jwt_token}
