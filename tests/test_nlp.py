from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot.moderation.analyzer import analyze_text

messages = [
    "Hello everyone",
    "Great work team",
    "You are stupid",
    "你很丑",
    "U sangat hodoh",
    "This is awful",
    "bro ni memang annoying gila"
]

for msg in messages:
    print(analyze_text(msg))
