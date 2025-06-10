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
from app.model import Diary, ConversationLog  #  ConversationLog 모델 추가
#from app.main import get_db
from app.deps import get_db
import base64
from google.oauth2 import service_account

router = APIRouter()

# 환경 변수
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
# GOOGLE_STT_KEY_PATH = os.getenv("GOOGLE_STT_KEY_PATH")
# if GOOGLE_STT_KEY_PATH:
#     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_STT_KEY_PATH

# AUDIO_DIR = "generated_audio"
# os.makedirs(AUDIO_DIR, exist_ok=True)

# STT 처리를 위해 m4a → flac 파일 변환
def convert_m4a_to_flac(input_path):
    sound = AudioSegment.from_file(input_path, format="m4a")
    flac_path = input_path.replace(".m4a", ".flac")
    sound.export(flac_path, format="flac")
    return flac_path

# 사용자 입력에 특정 키워드가 포함되어 있으면 감정 모드(T/F)를 판단
def detect_mode(user_input, prev_mode="F"):
    user_input = user_input.lower()
    if any(k in user_input for k in ["이성적으로", "논리적으로", "냉정하게"]):
        return "T"
    elif any(k in user_input for k in ["공감", "감성적으로", "위로"]):
        return "F"
    return prev_mode

# GPT 메시지 생성
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

# 챗봇 응답 생성
def get_gpt_response(messages):
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()

# Google TTS API를 활용해 GPT 응답 텍스트를 mp3 음성으로 변환


def synthesize_speech_base64(text: str) -> str:
    try:
        google_key_json = os.getenv("GOOGLE_STT_KEY")
        key_dict = json.loads(google_key_json)
        credentials = service_account.Credentials.from_service_account_info(key_dict)

        client = texttospeech.TextToSpeechClient(credentials=credentials)

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        audio_base64 = base64.b64encode(response.audio_content).decode("utf-8")
        return audio_base64

    except Exception as e:
        print("❌ TTS 변환 오류:", e)
        raise RuntimeError(f"TTS 변환 실패: {str(e)}")


# 대화 내역을 ConversationLog 테이블에 저장
def save_chat_log_db(db: Session, diary_id: int, user_input: str, response: str, mode: str, audio_url: str = None):
    log = ConversationLog(
        diary_id=diary_id,
        user_input=user_input,
        response=response,
        mode=mode,
        audio_url=audio_url
    )
    db.add(log)
    db.commit()

# 일기 텍스트 조회
# @router.get("/diary/text/{diary_id}")
# async def get_diary_text(diary_id: int, db: Session = Depends(get_db)):
#     diary = db.query(Diary).filter(Diary.id == diary_id).first()
#     if not diary:
#         return JSONResponse(status_code=404, content={"error": "일기 내용을 찾을 수 없습니다."})
#     return {
#         "text": {
#             "id": diary.id,
#             "content": diary.content,
#             "emotion": diary.emotion,
#             "confidence": diary.confidence,
#             "date": diary.date
#         }
#     }

# 프론트에서 diary_id를 전달하면 해당 일기 내용을 기반으로 첫 질문 생성 후 질문 TTS 변환 후 오디오 저장
@router.post("/generate-question")
async def generate_question(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        diary_id = body.get("diary_id")

        if not diary_id:
            return JSONResponse(status_code=400, content={"error": "diary_id is required"})

        diary = db.query(Diary).filter(Diary.id == int(diary_id)).first()
        if not diary:
            return JSONResponse(status_code=404, content={"error": "일기 내용을 찾을 수 없습니다."})

        diary_content = diary.content
        #print("📖 일기 내용:", diary_content)

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

        try:
            client = openai.OpenAI()
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=300,
            )
            question = completion.choices[0].message.content.strip()
            #print("🧠 생성된 질문:", question)
        except Exception as gpt_error:
            #print("❌ GPT 응답 실패:", gpt_error)
            return JSONResponse(status_code=500, content={"error": "GPT 응답 실패"})

        # TTS로 변환
        try:
            # TTS → base64
            audio_base64 = synthesize_speech_base64(question)

        except Exception as tts_error:
            #print("❌ TTS 변환 실패:", tts_error)
            return JSONResponse(status_code=500, content={"error": "TTS 변환 실패~"})

        return {
            "question": question,
            "audio_base64": audio_base64
        }

    except Exception as e:
        #print("❌ 최상위 에러:", e)
        return JSONResponse(status_code=500, content={"error": "질문 생성 실패"})



# 음성 업로드 및 대화 처리
@router.post("/upload-base64")
async def upload_audio_base64(request: Request, db: Session = Depends(get_db)):
    try:
        # 1. 요청 데이터 수신 및 검증
        try:
            data = await request.json()
            audio_base64 = data.get("audio_base64")
            history = data.get("history")
            diary_id = data.get("diary_id")
            if not audio_base64 or not diary_id or not history:
                return JSONResponse(status_code=400, content={"error": "audio_base64, diary_id, history는 필수입니다."})
        except Exception as parse_err:
            return JSONResponse(status_code=400, content={"error": f"요청 JSON 파싱 실패: {str(parse_err)}"})

        # 2. history JSON 변환
        try:
            history_data = history if isinstance(history, list) else json.loads(history)
        except Exception as hist_err:
            return JSONResponse(status_code=400, content={"error": f"history 파싱 실패: {str(hist_err)}"})

        # 3. base64 → 파일 저장
        try:
            audio_bytes = base64.b64decode(audio_base64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
                tmp.write(audio_bytes)
                m4a_path = tmp.name
        except Exception as b64_err:
            return JSONResponse(status_code=400, content={"error": f"base64 디코딩 또는 파일 저장 실패: {str(b64_err)}"})

        # 4. flac 변환
        try:
            flac_path = convert_m4a_to_flac(m4a_path)
        except Exception as convert_err:
            return JSONResponse(status_code=500, content={"error": f"m4a → flac 변환 실패: {str(convert_err)}"})

        # 5. STT
        try:
            client = speech.SpeechClient()
            with open(flac_path, "rb") as audio_file:
                content = audio_file.read()

            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
                sample_rate_hertz=16000,
                language_code="ko-KR",
            )
            stt_result = client.recognize(config=config, audio=audio)

            if not stt_result.results:
                return JSONResponse(status_code=400, content={"error": "STT 결과가 없습니다."})

            user_input = " ".join([r.alternatives[0].transcript for r in stt_result.results])
        except Exception as stt_err:
            return JSONResponse(status_code=500, content={"error": f"STT 실패: {str(stt_err)}"})

        # 6. 감정 모드 판단 및 GPT 호출
        try:
            prev_mode = history_data[-1].get("mode", "F") if history_data else "F"
            mode = detect_mode(user_input, prev_mode)

            messages = build_messages(history_data, user_input, mode)
            response_text = get_gpt_response(messages)
        except Exception as gpt_err:
            return JSONResponse(status_code=500, content={"error": f"GPT 응답 실패: {str(gpt_err)}"})

        # 7. TTS
        try:
            audio_base64_response = synthesize_speech_base64(response_text)
        except Exception as tts_err:
            return JSONResponse(status_code=500, content={"error": f"TTS 변환 실패: {str(tts_err)}"})

        # 8. DB 저장
        try:
            save_chat_log_db(
                db=db,
                diary_id=int(diary_id),
                user_input=user_input,
                response=response_text,
                mode=mode,
            )
        except Exception as db_err:
            return JSONResponse(status_code=500, content={"error": f"대화 저장 실패: {str(db_err)}"})

        # ✅ 성공 응답
        return {
            "input": user_input,
            "response": response_text,
            "audio_base64": audio_base64_response,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"알 수 없는 서버 오류: {str(e)}"})





# # 오디오 파일 반환
# @router.get("/audio/{filename}")
# async def get_audio(filename: str):
#     path = os.path.join(AUDIO_DIR, filename)
#     if os.path.exists(path):
#         return FileResponse(path, media_type="audio/mpeg")
#     return {"error": "파일이 존재하지 않습니다."}

# 대화 기록 조회 (DB 기반)
@router.get("/chat-history")
async def get_chat_history(diary_id: int, db: Session = Depends(get_db)):
    logs = (
        db.query(ConversationLog)
        .filter(ConversationLog.diary_id == diary_id)
        .order_by(ConversationLog.created_at)
        .all()
    )

    result = [
        {
            "user_input": log.user_input,
            "response": log.response,
            "mode": log.mode,
            #"audio_url": log.audio_url,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]
    return {"logs": result}
