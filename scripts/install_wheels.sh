#!/usr/bin/env bash

# Enhanced install script with aggressive constraint options to prevent backtracking

set -e

echo "=== Installing SAGE wheels with optimized dependency resolution ==="

# Ensure pip and wheel tools are up-to-date
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Pre-install numpy and scipy to pull binary wheels and avoid source builds
echo "Pre-installing numpy and scipy with binary wheels..."
pip install numpy scipy --prefer-binary --only-binary=:all:

# Create temp directory for environment variables
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_WARN_CONFLICTS=1

# Install sage with comprehensive constraints and options to speed up resolution
echo "Installing SAGE with aggressive constraint options..."
pip install sage \
  --find-links=./build/wheels \
  --constraint=constraints.txt \
  --constraint=./scripts/constraints.txt \
  --prefer-binary \
  --only-binary=:all: \
  --no-deps-check \
  --disable-pip-version-check \
  --no-warn-conflicts \
  --timeout=300 \
  --retries=3 \
  --cache-dir=/tmp/pip-cache \
  2>&1 | tee install.log

echo "Installation complete!" 