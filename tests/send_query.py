import requests

url = "http://127.0.0.1:8000/query"
data = {"query": "What is Newton's second law?"}

response = requests.post(url, json=data)
print(response)
