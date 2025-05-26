# app/auth_google.py

from fastapi import APIRouter, HTTPException
import httpx, os
from app.utils import create_access_token
from app import model, database

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

@router.get("/auth/google/callback")
async def google_callback(code: str):
    # 1. 액세스 토큰 요청
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=token_data)
        token_json = token_res.json()
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="구글 토큰 요청 실패")

        # 2. 사용자 정보 요청
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        user_res = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_res.json()
        email = user_info.get("email")
        name = user_info.get("name")

        if not email:
            raise HTTPException(status_code=400, detail="구글 이메일을 가져올 수 없습니다.")

        # 3. DB 저장 or 로그인 처리
        try:
            db = database.SessionLocal()
            user = db.query(model.User).filter(model.User.email == email).first()
            if not user:
                name = user_info.get("name")  # ← 여기서 이름 추출
                user = model.User(
                    email=email,
                    name=name,  # ← 모델에 추가된 name 필드
                    hashed_password="google-oauth"
                )
                db.add(user)
                db.commit()
        finally:
            db.close()

        # 4. JWT 발급
        jwt_token = create_access_token({"sub": email})
        return {"access_token": jwt_token}
