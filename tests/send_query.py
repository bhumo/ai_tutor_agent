import requests

url = "http://127.0.0.1:8000/query"
data = {"query": "2+2"}

response = requests.post(url, json=data)
print(response.json())
