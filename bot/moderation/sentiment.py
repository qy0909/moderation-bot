from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv

load_dotenv()

# -------------------------
# HF CLIENT (INIT ONCE)
# -------------------------
client = InferenceClient(
    api_key=os.getenv("HF_API_KEY")
)

MODEL_NAME = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"


# -------------------------
# SENTIMENT ANALYSIS
# -------------------------
def analyze_sentiment(text):
    try:
        result = client.text_classification(
            text,
            model=MODEL_NAME
        )

        if not result or len(result) == 0:
            return {
                "polarity": "UNKNOWN",
                "confidence": 0.0
            }

        output = result[0]

        return {
            "polarity": output.get("label", "UNKNOWN").upper(),
            "confidence": float(output.get("score", 0.0))
        }

    except Exception:
        return {
            "polarity": "UNKNOWN",
            "confidence": 0.0
        }


# -------------------------
# NORMALIZATION (UNCHANGED LOGIC)
# -------------------------
def normalize_sentiment(result):
    polarity = result.get("polarity", "UNKNOWN").upper()
    confidence = result.get("confidence", 0.0)

    if polarity == "POSITIVE":
        return confidence
    elif polarity == "NEGATIVE":
        return -confidence

    return 0.0