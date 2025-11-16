#!/bin/bash
# cURL Examples for SAGE Gateway

BASE_URL="http://localhost:8000"

echo "=== Health Check ==="
curl -X GET $BASE_URL/health
echo -e "\n"

echo "=== Non-streaming Chat Completion ==="
curl -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sage-token" \
  -d '{
    "model": "sage-default",
    "messages": [
      {"role": "user", "content": "Hello, SAGE!"}
    ],
    "stream": false
  }'
echo -e "\n"

echo "=== Streaming Chat Completion ==="
curl -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sage-token" \
  -d '{
    "model": "sage-default",
    "messages": [
      {"role": "user", "content": "Count from 1 to 3"}
    ],
    "stream": true
  }'
echo -e "\n"

echo "=== List Sessions ==="
curl -X GET $BASE_URL/sessions
echo -e "\n"
