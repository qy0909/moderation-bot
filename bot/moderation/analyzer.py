from .sentiment import analyze_sentiment, normalize_sentiment
from .toxicity import analyze_toxicity
from .fallback_model import fallback_sentiment, fallback_toxicity


def analyze_text(text):
    # -------------------------
    # PRIMARY: Hugging Face API
    # -------------------------
    sentiment = analyze_sentiment(text)
    toxicity = analyze_toxicity(text)

    # -------------------------
    # FALLBACK IF API FAILS
    # -------------------------
    if sentiment["polarity"] == "UNKNOWN":
        sentiment = fallback_sentiment(text)

    if toxicity["label"] == "unknown":
        toxicity = fallback_toxicity(text)

    return {
    "text": text,
    "sentiment": normalize_sentiment(sentiment),
    "sentiment_label": sentiment["polarity"],
    "toxicity": toxicity["score"],
    "toxicity_label": toxicity["label"],
    "severity": toxicity.get("severity", "non-toxic"),
    "confidence": sentiment["confidence"]
    }