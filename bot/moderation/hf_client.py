import os
import requests
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")

if not HF_API_KEY:
    raise ValueError("HF_API_KEY is missing in .env file")

HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}"
}


def query_model(api_url, text):
    payload = {"inputs": text}

    try:
        response = requests.post(
            api_url,
            headers=HEADERS,
            json=payload,
            timeout=15
        )

        if response.status_code != 200:
            return None

        try:
            return response.json()
        except:
            return None

    except requests.exceptions.RequestException:
        return None