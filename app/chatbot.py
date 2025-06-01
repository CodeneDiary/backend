from fastapi import APIRouter, UploadFile, File, Form
from typing import List
import openai, os, tempfile, json
from dotenv import load_dotenv
from google.cloud import speech
from pydub import AudioSegment

router = APIRouter()

# 환경변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_STT_KEY_PATH = os.getenv("GOOGLE_STT_KEY_PATH")

if GOOGLE_STT_KEY_PATH:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_STT_KEY_PATH


# m4a → flac 변환 함수
def convert_m4a_to_flac(input_path):
    sound = AudioSegment.from_file(input_path, format="m4a")
    flac_path = input_path.replace(".m4a", ".flac")
    sound.export(flac_path, format="flac")
    return flac_path


# 키워드 기반 모드 감지
def detect_mode(user_input: str, prev_mode: str = "F"):
    user_input = user_input.lower()
    if any(keyword in user_input for keyword in ["이성적으로", "논리적으로", "현실적으로", "냉정하게"]):
        return "T"
    elif any(keyword in user_input for keyword in ["공감", "위로", "감성적으로", "따뜻하게", "위로해줘"]):
        return "F"
    else:
        return prev_mode


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


# GPT 응답 생성
def get_gpt_response(messages):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=400
    )
    return response.choices[0].message.content.strip()

@router.get("/upload/test")
def upload_test():
    return {"message": "/upload 라우터가 정상 등록되어 있습니다."}

# /upload 라우터
@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    history: str = Form(default="[]")
):
    history_data = json.loads(history)

    # 1. m4a 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(await file.read())
        m4a_path = tmp.name

    # 2. flac 변환
    flac_path = convert_m4a_to_flac(m4a_path)

    # 3. 음성 인식 (STT)
    client = speech.SpeechClient()
    with open(flac_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code="ko-KR"
    )

    response = client.recognize(config=config, audio=audio)
    user_input = " ".join([r.alternatives[0].transcript for r in response.results])

    # 4. 모드 자동 판단 (히스토리에서 마지막 모드 or 기본 F)
    prev_mode = history_data[-1].get("mode", "F") if history_data else "F"
    mode = detect_mode(user_input, prev_mode)

    # 5. GPT 메시지 구성 & 응답 생성
    messages = build_messages(history_data, user_input, mode)
    response_text = get_gpt_response(messages)

    return {
        "input": user_input,
        "response": response_text
    }
