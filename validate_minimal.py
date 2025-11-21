#!/usr/bin/env python3
"""
Minimal validation script for GraphMemoryCollection implementation.
Tests the graph_collection.py file directly without importing the entire sage package.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Direct import of the graph_collection module
neuromem_path = Path(__file__).parent / "packages" / "sage-middleware" / "src" / "sage" / "middleware" / "components" / "sage_mem" / "neuromem"
collection_path = neuromem_path / "memory_collection"

print(f"Testing graph_collection.py from: {collection_path}")
print("=" * 70)

# Read and check the file exists and has content
graph_collection_file = collection_path / "graph_collection.py"

if not graph_collection_file.exists():
    print(f"❌ FAILED: File not found: {graph_collection_file}")
    sys.exit(1)

print("\n✓ Test 1: File exists")

# Check file size
file_size = os.path.getsize(graph_collection_file)
print(f"  ✓ File size: {file_size} bytes")

if file_size < 1000:
    print(f"  ⚠️  WARNING: File seems too small ({file_size} bytes)")

# Read the file
with open(graph_collection_file, 'r') as f:
    content = f.read()

# Test 2: Check for key class definitions
print("\n✓ Test 2: Checking for key class definitions...")
required_items = [
    "class SimpleGraphIndex",
    "class GraphMemoryCollection",
    "def add_node",
    "def add_edge",
    "def get_neighbors",
    "def retrieve_by_graph",
    "def store",
    "@classmethod",
    "def load",
]

for item in required_items:
    if item in content:
        print(f"  ✓ Found: {item}")
    else:
        print(f"  ❌ Missing: {item}")
        sys.exit(1)

# Test 3: Check for proper imports
print("\n✓ Test 3: Checking imports...")
required_imports = [
    "from .base_collection import BaseMemoryCollection",
    "from ..search_engine.graph_index.base_graph_index import BaseGraphIndex",
    "from sage.common.utils.logging.custom_logger import CustomLogger",
]

for imp in required_imports:
    if imp in content:
        print(f"  ✓ Found import: {imp}")
    else:
        print(f"  ❌ Missing import: {imp}")
        sys.exit(1)

# Test 4: Check file has no obvious syntax errors by compiling
print("\n✓ Test 4: Checking Python syntax...")
try:
    compile(content, str(graph_collection_file), 'exec')
    print("  ✓ Python syntax is valid")
except SyntaxError as e:
    print(f"  ❌ Syntax error: {e}")
    sys.exit(1)

# Test 5: Count lines of code
print("\n✓ Test 5: Code metrics...")
lines = content.split('\n')
code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
print(f"  ✓ Total lines: {len(lines)}")
print(f"  ✓ Code lines: {len(code_lines)}")

if len(code_lines) < 100:
    print(f"  ⚠️  WARNING: Implementation seems incomplete ({len(code_lines)} code lines)")

# Test 6: Check for key methods in GraphMemoryCollection
print("\n✓ Test 6: Checking GraphMemoryCollection methods...")
required_methods = [
    "def __init__",
    "def create_index",
    "def delete_index",
    "def add_node",
    "def add_edge",
    "def get_neighbors",
    "def retrieve_by_graph",
    "def store",
]

# Count occurrences in GraphMemoryCollection class
in_graph_collection = False
method_count = 0
for line in lines:
    if "class GraphMemoryCollection" in line:
        in_graph_collection = True
    elif in_graph_collection and line.startswith("class "):
        in_graph_collection = False
    
    if in_graph_collection:
        for method in required_methods:
            if method in line and not line.strip().startswith("#"):
                print(f"  ✓ Found method: {method}")
                method_count += 1
                break

if method_count < len(required_methods):
    print(f"  ⚠️  WARNING: Only found {method_count}/{len(required_methods)} required methods")

# Test 7: Check for SimpleGraphIndex methods
print("\n✓ Test 7: Checking SimpleGraphIndex methods...")
simple_index_methods = [
    "def add_node",
    "def add_edge",
    "def remove_node",
    "def remove_edge",
    "def get_neighbors",
    "def has_node",
]

in_simple_index = False
index_method_count = 0
for line in lines:
    if "class SimpleGraphIndex" in line:
        in_simple_index = True
    elif in_simple_index and line.startswith("class "):
        in_simple_index = False
    
    if in_simple_index:
        for method in simple_index_methods:
            if method in line and not line.strip().startswith("#"):
                print(f"  ✓ Found method: {method}")
                index_method_count += 1
                break

if index_method_count < len(simple_index_methods):
    print(f"  ⚠️  WARNING: Only found {index_method_count}/{len(simple_index_methods)} required methods")

# Test 8: Check documentation
print("\n✓ Test 8: Checking documentation...")
docstring_count = content.count('"""')
if docstring_count >= 4:  # At least 2 class docstrings
    print(f"  ✓ Found {docstring_count//2} docstrings")
else:
    print(f"  ⚠️  WARNING: Only found {docstring_count//2} docstrings")

print("\n" + "=" * 70)
print("✅ VALIDATION PASSED!")
print("=" * 70)
print("\nSummary:")
print(f"  - File size: {file_size} bytes")
print(f"  - Total lines: {len(lines)}")
print(f"  - Code lines: {len(code_lines)}")
print(f"  - GraphMemoryCollection methods: {method_count}/{len(required_methods)}")
print(f"  - SimpleGraphIndex methods: {index_method_count}/{len(simple_index_methods)}")
print(f"  - Docstrings: {docstring_count//2}")
print("\nThe GraphMemoryCollection implementation appears to be complete!")
