#!/usr/bin/env bash
# Ensure pip and wheel tools are up-to-date
pip install --upgrade pip setuptools wheel
# Pre-install numpy and scipy to pull binary wheels and avoid source builds
pip install numpy scipy
pip install sage --find-links=./build/wheels   --only-binary=:all: --fast-deps