import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

client = InferenceClient(api_key=os.getenv("HF_API_KEY"))

EMOTION_MODEL = "tabularisai/multilingual-emotion-classification"


def analyze_emotion(text):
    try:
        result = client.text_classification(
            text,
            model=EMOTION_MODEL
        )

        if not result:
            return {
                "emotion": "unknown",
                "confidence": 0.0
            }

        # API returns sorted list (highest score first)
        top = result[0]

        return {
            "emotion": top.get("label", "unknown").lower(),
            "confidence": float(top.get("score", 0.0))
        }

    except Exception as e:
        print("EMOTION API ERROR:", e)
        return {
            "emotion": "unknown",
            "confidence": 0.0
        }