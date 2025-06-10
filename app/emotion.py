# app/emotion.py

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F

model_name = "M1NJ1/Multimodal_Sentiment_Analysis"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForSequenceClassification.from_pretrained(model_name, trust_remote_code=True)

label_map = {
    0: "갈망", 1: "감사", 2: "걱정", 3: "공감", 4: "공포", 5: "괴로움",
    6: "그리움", 7: "기쁨", 8: "놀람", 9: "당황", 10: "답답", 11: "당혹",
    12: "두려움", 13: "분노", 14: "불안", 15: "비참", 16: "사랑", 17: "상처",
    18: "상실", 19: "서운", 20: "설렘", 21: "슬픔", 22: "스트레스", 23: "실망",
    24: "신남", 25: "억울", 26: "외로움", 27: "우울", 28: "의심", 29: "자괴감",
    30: "죄책감", 31: "창피", 32: "충격", 33: "쾌감", 34: "편안", 35: "후련함",
    36: "희망", 37: "희열", 38: "혐오", 39: "혼란", 40: "기대", 41: "무서움",
    42: "좌절", 43: "흥미"
}


def predict_emotion(text: str, threshold: float = 0.3):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)[0]  # shape: (num_labels,)

    results = []
    for i, p in enumerate(probs):
        if p.item() >= threshold:
            results.append({
                "label": label_map[i],
                "confidence": round(p.item(), 4)
            })

    # 내림차순 정렬
    results.sort(key=lambda x: x["confidence"], reverse=True)

    # 아무 감정도 없으면 메시지 반환
    if not results:
        return [{
            "label": "감정을 알 수 없음",
            "confidence": 0.0
        }]

    return results
