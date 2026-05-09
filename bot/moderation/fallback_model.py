from transformers import pipeline

# -------------------------
# MODEL CACHE (LOAD ONCE)
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
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
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
            model="unitary/toxic-bert"
        )

    return _toxicity_model


# -------------------------
# FALLBACK SENTIMENT
# -------------------------
def fallback_sentiment(text):
    model = get_sentiment_model()
    result = model(text)[0]

    return {
        "polarity": result.get("label", "UNKNOWN").upper(),
        "confidence": float(result.get("score", 0.0))
    }


# -------------------------
# FALLBACK TOXICITY
# -------------------------
def fallback_toxicity(text):
    model = get_toxicity_model()
    result = model(text)[0]

    score = float(result.get("score", 0.0))
    toxicity_label = "toxic" if score > 0.5 else "non-toxic"

    severity = (
        "severe toxic" if score >= 0.85 else
        "toxic" if score >= 0.60 else
        "non-toxic"
    )

    return {
        "label": toxicity_label,
        "score": score,
        "severity": severity
    }