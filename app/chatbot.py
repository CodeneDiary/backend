from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import openai
import os
import tempfile
import json
import uuid
from dotenv import load_dotenv
from google.cloud import speech, texttospeech
from pydub import AudioSegment
from app.model import Diary  # SQLAlchemy Diary 모델
from app.main import get_db  # 세션 의존성

router = APIRouter()

# 환경 변수
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_STT_KEY_PATH = os.getenv("GOOGLE_STT_KEY_PATH")
if GOOGLE_STT_KEY_PATH:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_STT_KEY_PATH

AUDIO_DIR = "generated_audio"
LOG_DIR = "chat_logs"
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# m4a → flac 변환
def convert_m4a_to_flac(input_path):
    sound = AudioSegment.from_file(input_path, format="m4a")
    flac_path = input_path.replace(".m4a", ".flac")
    sound.export(flac_path, format="flac")
    return flac_path

# 대화 스타일 판별
def detect_mode(user_input, prev_mode="F"):
    user_input = user_input.lower()
    if any(k in user_input for k in ["이성적으로", "논리적으로", "냉정하게"]):
        return "T"
    elif any(k in user_input for k in ["공감", "감성적으로", "위로"]):
        return "F"
    return prev_mode

# GPT 메시지 구성
def build_messages(history, user_input, mode):
    messages = [
        {
            "role": "system",
            "content": (
                "당신은 감정 상담을 해주는 따뜻한 챗봇입니다. "
                "사용자의 감정을 이해하고 요청한 스타일에 따라 답변해야 합니다. "
                "T: 이성적 조언 / F: 감성적 공감. "
                "무조건 부드러운 어조를 유지하세요."
            )
        }
    ]
    for turn in history:
        messages.append({"role": "user", "content": turn["user_input"]})
        messages.append({"role": "assistant", "content": turn["response"]})
    prompt = f"[요청 스타일: {mode}]\n{user_input}"
    messages.append({"role": "user", "content": prompt})
    return messages

# GPT 응답 생성
def get_gpt_response(messages):
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()

# TTS 변환
def synthesize_speech(text, output_path):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="ko-KR",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
    return output_path

# 대화 기록 저장
def save_chat_log(diary_id, user_input, response):
    log_path = os.path.join(LOG_DIR, f"{diary_id}.json")
    log = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
    log.append({"user_input": user_input, "response": response})
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

# DB에서 일기 내용 조회 API
@router.get("/diary/text/{diary_id}")
async def get_diary_text(diary_id: int, db: Session = Depends(get_db)):
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if not diary:
        return JSONResponse(status_code=404, content={"error": "일기 내용을 찾을 수 없습니다."})
    return {
        "text": {
            "id": diary.id,
            "content": diary.content,
            "emotion": diary.emotion,
            "confidence": diary.confidence,
            "date": diary.date
        }
    }

# 첫 질문 생성 API – DB에서 diary_id로 일기 조회
@router.post("/generate-question")
async def generate_question(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        body = await request.json()
        diary_id = body.get("diary_id")
        if not diary_id:
            return JSONResponse(status_code=400, content={"error": "diary_id is required"})

        diary = db.query(Diary).filter(Diary.id == diary_id).first()
        if not diary:
            return JSONResponse(status_code=404, content={"error": "일기 내용을 찾을 수 없습니다."})

        diary_content = diary.content

        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 감정 상담 챗봇입니다. 사용자가 작성한 일기 내용을 바탕으로 감정을 더 잘 파악할 수 있는 첫 질문을 생성하세요. "
                    "질문은 너무 길지 않게 하고, 감정을 유도하는 부드러운 문장으로 시작하세요."
                )
            },
            {"role": "user", "content": f"일기 내용: {diary_content}"}
        ]

        client = openai.OpenAI()
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )
        question = completion.choices[0].message.content.strip()
        return {"question": question}

    except Exception as e:
        print("질문 생성 실패:", e)
        return JSONResponse(status_code=500, content={"error": "질문 생성 실패"})

# 음성 업로드 및 대화 처리
@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    history: str = Form(...),
    diary_id: str = Form(...)
):
    history_data = json.loads(history)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(await file.read())
        m4a_path = tmp.name

    flac_path = convert_m4a_to_flac(m4a_path)
    client = speech.SpeechClient()
    with open(flac_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code="ko-KR"
    )
    stt_result = client.recognize(config=config, audio=audio)
    user_input = " ".join([r.alternatives[0].transcript for r in stt_result.results])

    prev_mode = history_data[-1].get("mode", "F") if history_data else "F"
    mode = detect_mode(user_input, prev_mode)

    messages = build_messages(history_data, user_input, mode)
    response_text = get_gpt_response(messages)

    filename = f"{uuid.uuid4()}.mp3"
    output_path = os.path.join(AUDIO_DIR, filename)
    synthesize_speech(response_text, output_path)
    save_chat_log(diary_id, user_input, response_text)

    return {
        "input": user_input,
        "response": response_text,
        "audio_url": f"/audio/{filename}"
    }

# 오디오 파일 반환
@router.get("/audio/{filename}")
async def get_audio(filename: str):
    path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg")
    return {"error": "파일이 존재하지 않습니다."}

# 대화 기록 반환
@router.get("/chat-history")
async def get_chat_history(diary_id: str):
    path = os.path.join(LOG_DIR, f"{diary_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {"logs": json.load(f)}
    return {"logs": []}
