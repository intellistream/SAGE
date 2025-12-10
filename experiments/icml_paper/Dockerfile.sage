# SAGE Experiment Image
# Lightweight image for gateway, embedding, and benchmark client

FROM python:3.11-slim

LABEL maintainer="SAGE Team"
LABEL description="SAGE Experiment Runner for ICML Paper"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install SAGE packages
WORKDIR /app

# Copy only necessary packages for experiments
COPY packages/sage-common /app/packages/sage-common
COPY packages/sage-gateway /app/packages/sage-gateway
COPY packages/sage-benchmark /app/packages/sage-benchmark
COPY packages/sage /app/packages/sage

# Install packages
RUN pip install --no-cache-dir \
    /app/packages/sage-common \
    /app/packages/sage-gateway \
    /app/packages/sage-benchmark \
    /app/packages/sage

# Install additional dependencies for experiments
RUN pip install --no-cache-dir \
    typer \
    aiohttp \
    pyyaml \
    matplotlib \
    pandas \
    numpy \
    rich \
    httpx

# Copy experiment scripts
COPY experiments/icml_paper/scripts /app/scripts

# Default command
CMD ["python", "-m", "sage.gateway"]
