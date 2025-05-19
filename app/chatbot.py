import openai

openai.api_key = "YOUR_API_KEY"  # 나중에 .env로 분리 추천

def call_chatbot(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 또는 사용 중인 모델 이름
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "챗봇 응답 중 오류가 발생했습니다."
