import requests
import json

url = "https://api.bochaai.com/v1/web-search"

payload = json.dumps({
  "query": "天空为什么是蓝色的？",
  "summary": True,
  "count": 10,
  "page": 1
})

headers = {
  'Authorization': 'sk-3e0704d84d954379b5c38d089ddd2b96',
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.json())