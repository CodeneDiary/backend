from fastapi import APIRouter, UploadFile, File, Form
from typing import List
import openai, os, tempfile, json
from dotenv import load_dotenv
from google.cloud import speech

router = APIRouter()

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_STT_KEY_PATH = os.getenv("GOOGLE_STT_KEY_PATH")

if GOOGLE_STT_KEY_PATH:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_STT_KEY_PATH

RENDER_URL = os.getenv("RENDER_URL", "https://gamja-friend.onrender.com")

# GPT 메시지 구성
def build_messages(history, user_input, mode):
    messages = [{
        "role": "system",
        "content": (
            "당신은 감정 상담을 해주는 따뜻한 챗봇입니다. "
            "사용자의 감정을 이해하고 요청한 스타일에 따라 답변해야 합니다. "
            "T: 이성적 조언 / F: 감성적 공감. "
            "무조건 부드러운 어조를 유지하세요."
        )
    }]
    for turn in history:
        messages.append({"role": "user", "content": turn["user_input"]})
        messages.append({"role": "assistant", "content": turn["response"]})
    prompt = f"[요청 스타일: {mode}]\n{user_input}"
    messages.append({"role": "user", "content": prompt})
    return messages

def get_gpt_response(messages):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=400
    )
    return response.choices[0].message.content.strip()

@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    history: str = Form(default="[]")
):
    history_data = json.loads(history)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".flac") as tmp:
        tmp.write(await file.read())
        audio_path = tmp.name

    client = speech.SpeechClient()
    with open(audio_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code="ko-KR"
    )

    response = client.recognize(config=config, audio=audio)
    user_input = " ".join([r.alternatives[0].transcript for r in response.results])

    messages = build_messages(history_data, user_input, "F")
    response_text = get_gpt_response(messages)

    return {
        "input": user_input,
        "response": response_text,
    }

