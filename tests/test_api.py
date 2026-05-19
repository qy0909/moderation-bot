from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests

url = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"

print(requests.get(url).status_code)
