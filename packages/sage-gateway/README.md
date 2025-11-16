# sage-gateway

**SAGE API Gateway** - OpenAI/Anthropic compatible protocol adapter for SAGE framework.

## Overview

`sage-gateway` provides familiar API interfaces (OpenAI, Anthropic) that translate requests into
SAGE's DataStream execution model. This allows users to interact with SAGE using APIs they already
know, without learning new protocols.

## Features

- ✅ **OpenAI Compatible API** - `/v1/chat/completions` endpoint
- ✅ **Streaming Support** - Server-Sent Events (SSE) for real-time responses
- ✅ **Session Management** - Conversation history and context handling
- 🚧 **Anthropic Compatible API** - `/v1/messages` endpoint (coming soon)
- 🚧 **WebSocket Support** - Real-time bidirectional streaming (coming soon)

## Installation

```bash
# From PyPI (when published)
pip install sage-gateway

# From source (development)
cd packages/sage-gateway
pip install -e .
```

## Quick Start

### Start the Gateway Server

```bash
# Using the CLI
sage-gateway --host 0.0.0.0 --port 8000

# Or with Python
python -m sage.gateway.server
```

### Call with OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sage-token",  # pragma: allowlist secret  # Any non-empty string
)

response = client.chat.completions.create(
    model="sage-default",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

### Call with cURL

```bash
# Non-streaming
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sage-token" \
  -d '{
    "model": "sage-default",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Streaming
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sage-token" \
  -d '{
    "model": "sage-default",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│          sage-gateway (L6)                      │
├─────────────────────────────────────────────────┤
│                                                  │
│  FastAPI Server                                 │
│  ├─ /v1/chat/completions (OpenAI compat)       │
│  ├─ /v1/messages (Anthropic compat)            │
│  └─ /health, /metrics                          │
│                                                  │
│  Adapters                                       │
│  ├─ OpenAI Protocol → SAGE Kernel              │
│  └─ Anthropic Protocol → SAGE Kernel           │
│                                                  │
│  Session Manager                                │
│  └─ Conversation history, context tracking     │
│                                                  │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│          sage-kernel (L3)                       │
│  DataStream API → Execution Engine              │
└─────────────────────────────────────────────────┘
```

## Configuration

Create a `.env` file or set environment variables:

```bash
# Server
SAGE_GATEWAY_HOST=0.0.0.0
SAGE_GATEWAY_PORT=8000
SAGE_GATEWAY_WORKERS=4

# Authentication (optional)
SAGE_GATEWAY_API_KEY=your-secret-key

# Session storage (optional)
SAGE_GATEWAY_SESSION_BACKEND=memory  # or redis
SAGE_GATEWAY_REDIS_URL=redis://localhost:6379

# Logging
SAGE_GATEWAY_LOG_LEVEL=INFO
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Start in development mode
uvicorn sage.gateway.server:app --reload --port 8000
```

## API Reference

### POST /v1/chat/completions

OpenAI-compatible chat completion endpoint.

**Request Body:**

```json
{
  "model": "sage-default",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 1.0,
  "max_tokens": null
}
```

**Response (non-streaming):**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677858242,
  "model": "sage-default",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

## License

MIT License - see LICENSE file for details.
