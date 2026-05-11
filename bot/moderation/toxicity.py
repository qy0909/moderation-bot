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

MODEL = "citizenlab/distilbert-base-multilingual-cased-toxicity"


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
                "confidence": 0.0,
                "severity": "non-toxic"
            }

        output = result[0]

        raw_label = output.label.lower()
        raw_score = float(output.score)

        # store original confidence
        confidence = raw_score

        # -------------------------
        # NORMALIZE MODEL OUTPUT
        # -------------------------
        if raw_label in ["not_toxic", "non-toxic", "safe", "label_0"]:
            label = "non-toxic"
            score = 1 - raw_score

        elif raw_label in ["toxic", "label_1"]:
            label = "toxic"
            score = raw_score

        else:
            label = "unknown"
            score = 0.0

        # -------------------------
        # SEVERITY LOGIC
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
            "confidence": confidence,
            "severity": severity
        }

    except Exception as e:
        print("TOXICITY ERROR:", e)

        return {
            "label": "unknown",
            "score": 0.0,
            "confidence": 0.0,
            "severity": "non-toxic"
        }