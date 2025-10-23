#!/usr/bin/env bash
# 1. Install dependencies
pip install --upgrade pip
pip install mkdocstrings[python]
pip install -r requirements.txt

# 2. Build the site
mkdocs build --clean
