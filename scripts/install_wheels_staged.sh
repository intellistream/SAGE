#!/usr/bin/env bash

# Staged installation script to avoid dependency backtracking hell
# This script installs dependencies in carefully ordered stages

set -e

echo "=== SAGE Staged Installation with Dependency Pre-resolution ==="

# Upgrade core tools first
echo "Stage 0: Upgrading core pip tools..."
pip install --upgrade pip setuptools wheel build

# Stage 1: Core system dependencies (no conflicts here)
echo "Stage 1: Installing core system dependencies..."
pip install --prefer-binary --only-binary=:all: \
  numpy==2.3.2 \
  scipy==1.16.1 \
  packaging==25.0 \
  typing-extensions==4.14.1 \
  six==1.17.0 \
  certifi==2025.8.3 \
  idna==3.10

# Stage 2: Core networking (fixed versions to prevent conflicts)
echo "Stage 2: Installing networking dependencies..."
pip install --prefer-binary --only-binary=:all: \
  httpcore==1.0.9 \
  h11==0.16.0 \
  sniffio==1.3.1 \
  anyio==4.10.0 \
  socksio==1.0.0 \
  httpx==0.28.1

# Stage 3: Async and HTTP stack
echo "Stage 3: Installing async and HTTP stack..."
pip install --prefer-binary --only-binary=:all: \
  attrs==25.3.0 \
  multidict==6.6.3 \
  frozenlist==1.7.0 \
  yarl==1.20.1 \
  propcache==0.3.2 \
  aiosignal==1.4.0 \
  aiohappyeyeballs==2.6.1 \
  aiohttp==3.12.15

# Stage 4: PyTorch ecosystem (largest dependencies)
echo "Stage 4: Installing PyTorch ecosystem..."
pip install --prefer-binary --only-binary=:all: \
  torch==2.3.0 \
  torchvision==0.18.0

# Stage 5: AWS and cloud dependencies
echo "Stage 5: Installing AWS dependencies..."
pip install --prefer-binary --only-binary=:all: \
  jmespath==1.0.1 \
  python-dateutil==2.9.0.post0 \
  urllib3==2.5.0 \
  botocore==1.37.1 \
  s3transfer==0.11.5 \
  boto3==1.37.1

# Stage 6: ML and AI dependencies
echo "Stage 6: Installing ML dependencies..."
pip install --prefer-binary --only-binary=:all: \
  joblib==1.5.1 \
  regex==2025.7.34 \
  tqdm==4.67.1 \
  pyyaml==6.0.2 \
  tokenizers==0.21.4 \
  huggingface-hub==0.34.3 \
  transformers==4.54.1

# Stage 7: FastAPI web framework
echo "Stage 7: Installing web framework..."
pip install --prefer-binary --only-binary=:all: \
  starlette==0.46.2 \
  fastapi==0.115.12 \
  uvicorn==0.34.3 \
  python-multipart==0.0.20

# Stage 8: Other important dependencies
echo "Stage 8: Installing remaining dependencies..."
pip install --prefer-binary --only-binary=:all: \
  pandas==2.3.1 \
  pytz==2025.2 \
  tzdata==2025.2 \
  python-dotenv==1.1.1 \
  dill==0.4.0 \
  msgpack==1.1.1 \
  protobuf==6.31.1 \
  grpcio==1.74.0 \
  ray==2.48.0

# Stage 9: Development and testing tools
echo "Stage 9: Installing development tools..."
pip install --prefer-binary --only-binary=:all: \
  rich==14.1.0 \
  typer==0.16.0 \
  pytest==8.4.1 \
  pytest-cov==6.2.1 \
  pytest-asyncio==1.1.0 \
  pytest-benchmark==5.1.0

# Stage 10: Finally install SAGE wheels
echo "Stage 10: Installing SAGE wheels..."
pip install \
  --find-links=./build/wheels \
  --prefer-binary \
  --no-deps \
  sage

echo "=== SAGE Installation Complete! ==="
echo "Verifying installation..."
python -c "import sage; print('SAGE imported successfully!')"
