from transformers import pipeline

# -------------------------
# MODEL CACHE
# -------------------------
_sentiment_model = None
_toxicity_model = None


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
# FALLBACK SENTIMENT
# -------------------------
def fallback_sentiment(text):
    model = get_sentiment_model()
    result = model(text)[0]

    polarity = result.get("label", "UNKNOWN").upper()
    confidence = float(result.get("score", 0.0))

    return {
        "polarity": polarity,
        "confidence": confidence
    }


# -------------------------
# FALLBACK TOXICITY
# -------------------------
def fallback_toxicity(text):
    model = get_toxicity_model()
    result = model(text)[0]

    raw_label = result.get("label", "").lower()
    raw_score = float(result.get("score", 0.0))

    # Match API normalization
    if raw_label in ["not_toxic", "non-toxic", "safe", "label_0"]:
        label = "non-toxic"
        score = 1 - raw_score

    elif raw_label in ["toxic", "label_1"]:
        label = "toxic"
        score = raw_score

    else:
        label = "unknown"
        score = 0.0

    # Match API severity thresholds
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