from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
import openai, os, tempfile, json, uuid
from dotenv import load_dotenv
from google.cloud import speech, texttospeech
from pydub import AudioSegment

router = APIRouter()

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_STT_KEY_PATH = os.getenv("GOOGLE_STT_KEY_PATH")

if GOOGLE_STT_KEY_PATH:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_STT_KEY_PATH

AUDIO_DIR = "generated_audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# m4a → flac 변환
def convert_m4a_to_flac(input_path):
    sound = AudioSegment.from_file(input_path, format="m4a")
    flac_path = input_path.replace(".m4a", ".flac")
    sound.export(flac_path, format="flac")
    return flac_path

# 감정 모드 판단 함수
def detect_mode(user_input, prev_mode="F"):
    user_input = user_input.lower()
    if any(k in user_input for k in ["이성적으로", "논리적으로", "냉정하게"]):
        return "T"
    elif any(k in user_input for k in ["공감", "감성적으로", "위로"]):
        return "F"
    return prev_mode

# GPT 메시지 구성 함수
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

# Google TTS 음성 생성 함수
def synthesize_speech(text, output_path):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="ko-KR",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(output_path, "wb") as out:
        out.write(response.audio_content)
    return output_path

# /upload 라우터
@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    history: str = Form(default="[]")
):
    history_data = json.loads(history)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(await file.read())
        m4a_path = tmp.name

    flac_path = convert_m4a_to_flac(m4a_path)

    # STT
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

    return {
        "input": user_input,
        "response": response_text,
        "audio_url": f"/audio/{filename}"
    }

# 음성 파일 제공
@router.get("/audio/{filename}")
async def get_audio(filename: str):
    path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg")
    return {"error": "파일이 존재하지 않습니다."}