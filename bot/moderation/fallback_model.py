from transformers import pipeline

# -------------------------
# MODEL CACHE
# -------------------------
_sentiment_model = None
_toxicity_model = None
_emotion_model = None


# -------------------------
# SENTIMENT MODEL
# -------------------------
def get_sentiment_model():
    global _sentiment_model

    if _sentiment_model is None:
        _sentiment_model = pipeline(
            "text-classification",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest"
        )

    return _sentiment_model


# -------------------------
# TOXICITY MODEL
# -------------------------
def get_toxicity_model():
    global _toxicity_model

    if _toxicity_model is None:
        _toxicity_model = pipeline(
            "text-classification",
            model="citizenlab/distilbert-base-multilingual-cased-toxicity"
        )

    return _toxicity_model


# -------------------------
# EMOTION MODEL
# -------------------------
def get_emotion_model():
    global _emotion_model

    if _emotion_model is None:
        _emotion_model = pipeline(
            "text-classification",
            model="tabularisai/multilingual-emotion-classification",
            top_k=None
        )

    return _emotion_model


# -------------------------
# SENTIMENT FALLBACK
# -------------------------
def fallback_sentiment(text):
    model = get_sentiment_model()
    result = model(text)[0]

    return {
        "polarity": result.get("label", "UNKNOWN").upper(),
        "confidence": float(result.get("score", 0.0))
    }


# -------------------------
# TOXICITY FALLBACK
# -------------------------
def fallback_toxicity(text):
    model = get_toxicity_model()
    result = model(text)[0]

    raw_label = result.get("label", "").lower()
    raw_score = float(result.get("score", 0.0))

    if raw_label in ["not_toxic", "non-toxic", "safe", "label_0"]:
        label = "non-toxic"
        score = 1 - raw_score

    elif raw_label in ["toxic", "label_1"]:
        label = "toxic"
        score = raw_score

    else:
        label = "unknown"
        score = 0.0

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

# -------------------------
# EMOTION FALLBACK
# -------------------------
def fallback_emotion(text):
    model = get_emotion_model()

    try:
        result = model(text)

        if not result:
            return {"emotion": "unknown", "confidence": 0.0}

        # HANDLE BOTH POSSIBLE FORMATS SAFELY
        first = result[0]

        # Case 1: [[{...}, {...}]]
        if isinstance(first, list):
            emotions = first

        # Case 2: [{...}, {...}]
        else:
            emotions = first if isinstance(first, list) else result

        # ensure list of dicts
        emotions = [e for e in emotions if isinstance(e, dict)]

        if not emotions:
            return {"emotion": "unknown", "confidence": 0.0}

        top = max(emotions, key=lambda x: x["score"])

        return {
            "emotion": top["label"].lower(),
            "confidence": float(top["score"])
        }

    except Exception as e:
        print("EMOTION ERROR:", e)
        return {"emotion": "unknown", "confidence": 0.0}