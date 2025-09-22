# SAGE Middleware

Streaming-Augmented Generative Execution Middleware - A comprehensive middleware framework for building AI-powered data processing pipelines.

## Overview

SAGE Middleware provides a robust foundation for building streaming data processing applications with AI capabilities. It integrates multiple AI providers, task queuing, authentication, and high-performance data processing components.

## Key Features

### 🤖 AI Integration
- **Multi-Provider Support**: OpenAI, Anthropic, Cohere, Ollama, ZhipuAI
- **LLM Integration**: Seamless integration with large language models
- **Embedding Support**: Vector embeddings with FAISS and other backends

### 📊 Data Processing
- **Vector Processing**: High-performance vector operations with candyFlow
- **RAG Support**: Retrieval-Augmented Generation pipelines
- **BM25 Integration**: Efficient text retrieval and ranking

### 🔄 Task Management
- **Celery Integration**: Distributed task queuing and processing
- **Async Processing**: Asynchronous task execution with aiohttp

### 🔐 Security & Auth
- **JWT Authentication**: Secure API authentication
- **Password Management**: Secure password hashing and validation

## Installation

```bash
pip install isage-middleware
```

### Optional Dependencies

```bash
# With VLLM support (requires CUDA)
pip install isage-middleware[vllm]

# With full SAGE framework
pip install isage-middleware[sage]
```

## Quick Start

```python
from sage.middleware.api.client import APIClient
from sage.middleware.auth.jwt import JWTManager

# Initialize components
client = APIClient()
jwt_manager = JWTManager()

# Use AI providers
response = client.chat_completion(
    provider="openai",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Architecture

### Core Components

- **API Layer**: RESTful API endpoints with authentication
- **Service Layer**: Business logic and AI provider integrations
- **Data Layer**: Vector processing and storage backends
- **Task Layer**: Asynchronous task processing with Celery

### Middleware Services

- **sage_db**: Database abstraction layer
- **sage_flow**: High-performance vector stream processing
- **sage_rag**: Retrieval-Augmented Generation pipelines

## Configuration

Create a configuration file:

```yaml
# config.yaml
middleware:
  auth:
    secret_key: "your-secret-key"
    algorithm: "HS256"

  providers:
    openai:
      api_key: "sk-..."
      base_url: "https://api.openai.com/v1"
```

## Development

```bash
# Clone the repository
git clone https://github.com/intellistream/sage.git
cd sage/packages/sage-middleware

# Install in development mode
pip install -e .
```

## Contributing

Please read our [Contributing Guide](../../CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## Authors

- **IntelliStream Team** - *Initial work* - [intellistream@outlook.com](mailto:intellistream@outlook.com)

## Acknowledgments

- Built on top of the SAGE framework
- Powered by various open-source AI and data processing libraries