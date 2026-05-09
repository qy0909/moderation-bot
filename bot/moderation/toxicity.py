import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

# -------------------------
# HF CLIENT
# -------------------------
client = InferenceClient(
    api_key=os.getenv("HF_API_KEY")
)

MODEL = "unitary/toxic-bert"


# -------------------------
# TOXICITY ANALYSIS
# -------------------------
def analyze_toxicity(text):
    try:
        result = client.text_classification(
            text,
            model=MODEL
        )

        if not result or len(result) == 0:
            return {
                "label": "unknown",
                "score": 0.0,
                "severity": "non-toxic"
            }

        output = result[0]

        score = float(output.get("score", 0.0))

        # 🚨 DO NOT trust model label
        label = "toxic" if score >= 0.5 else "non-toxic"

        # -------------------------
        # SEVERITY LOGIC (SPC READY)
        # -------------------------
        if score >= 0.85:
            severity = "severe toxic"
        elif score >= 0.60:
            severity = "toxic"
        else:
            severity = "non-toxic"

        return {
            "label": label,
            "score": score,
            "severity": severity
        }

    except Exception:
        return {
            "label": "unknown",
            "score": 0.0,
            "severity": "non-toxic"
        }