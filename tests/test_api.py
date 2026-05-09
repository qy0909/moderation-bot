import requests

url = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"

print(requests.get(url).status_code)