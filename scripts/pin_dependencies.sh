#!/usr/bin/env bash

# Script to update all SAGE package dependencies with pinned versions
# This will make pip install sage much faster by avoiding dependency backtracking

set -e

echo "=== Updating SAGE package dependencies with pinned versions ==="

# Create a mapping of package names to pinned versions based on installation logs
declare -A PINNED_VERSIONS=(
    # Core system
    ["numpy"]="==2.3.2"
    ["scipy"]="==1.16.1"
    ["pandas"]="==2.3.1"
    ["pyyaml"]="==6.0.2"
    ["PyYAML"]="==6.0.2" 
    ["python-dotenv"]="==1.1.1"
    ["dill"]="==0.4.0"
    ["msgpack"]="==1.1.1"
    ["protobuf"]="==6.31.1"
    ["psutil"]="==7.0.0"
    ["packaging"]="==25.0"
    ["typing-extensions"]="==4.14.1"
    
    # Web framework
    ["fastapi"]="==0.115.12"
    ["uvicorn"]="==0.34.3"
    ["starlette"]="==0.46.2"
    ["python-multipart"]="==0.0.20"
    ["h11"]="==0.16.0"
    
    # Network stack
    ["httpx"]="==0.28.1"
    ["httpcore"]="==1.0.9"
    ["socksio"]="==1.0.0"
    ["aiohttp"]="==3.12.15"
    ["aiohappyeyeballs"]="==2.6.1"
    ["aiosignal"]="==1.4.0"
    ["frozenlist"]="==1.7.0"
    ["propcache"]="==0.3.2"
    ["yarl"]="==1.20.1"
    ["multidict"]="==6.6.3"
    ["attrs"]="==25.3.0"
    ["requests"]="==2.32.4"
    ["charset-normalizer"]="==3.4.2"
    ["urllib3"]="==2.5.0"
    ["certifi"]="==2025.8.3"
    ["idna"]="==3.10"
    ["anyio"]="==4.10.0"
    ["sniffio"]="==1.3.1"
    
    # ML/AI
    ["torch"]="==2.3.0"
    ["torchvision"]="==0.18.0"
    ["transformers"]="==4.54.1"
    ["tokenizers"]="==0.21.4"
    ["accelerate"]="==1.9.0"
    ["huggingface-hub"]="==0.34.3"
    ["sentence-transformers"]="==5.0.0"
    ["InstructorEmbedding"]="==1.0.1"
    ["peft"]="==0.17.0"
    ["faiss-cpu"]="==1.9.0"
    ["bm25s"]="==0.2.13"
    ["rank-bm25"]="==0.2.2"
    ["PyStemmer"]="==3.0.0"
    
    # AWS
    ["aioboto3"]="==14.1.0"
    ["aiobotocore"]="==2.21.1"
    ["boto3"]="==1.37.1"
    ["botocore"]="==1.37.1"
    ["aiofiles"]="==24.1.0"
    ["aioitertools"]="==0.12.0"
    ["jmespath"]="==1.0.1"
    ["wrapt"]="==1.17.2"
    ["s3transfer"]="==0.11.5"
    
    # Ray/distributed
    ["ray"]="==2.48.0"
    ["grpcio"]="==1.74.0"
    
    # LLM services 
    ["openai"]="==1.98.0"
    ["ollama"]="==0.5.1"
    ["vllm"]="==0.10.0"
    ["zhipuai"]="==2.1.5.20250801"
    ["cohere"]="==5.16.2"
    
    # Task queue
    ["celery"]="==5.5.3"
    ["flower"]="==2.0.1"
    
    # Security
    ["passlib"]="==1.7.4"
    ["python-jose"]="==3.5.0"
    ["cryptography"]="==45.0.5"
    
    # Development tools
    ["rich"]="==14.1.0"
    ["typer"]="==0.16.0"
    ["pytest"]="==8.4.1"
    ["pytest-cov"]="==6.2.1"
    ["pytest-asyncio"]="==1.1.0"
    ["pytest-benchmark"]="==5.1.0"
    ["safety"]="==3.6.0"
    
    # Utilities
    ["jinja2"]="==3.1.6"
    ["Jinja2"]="==3.1.6"
    ["gitpython"]="==3.1.45"
    ["pathspec"]="==0.12.1"
    ["feedparser"]="==6.0.11"
    ["tomli"]="==2.2.1"
    ["tomli-w"]="==1.2.0"
    ["shellingham"]="==1.5.4"
    ["six"]="==1.17.0"
    ["python-dateutil"]="==2.9.0.post0"
    ["pytz"]="==2025.2"
    ["tzdata"]="==2025.2"
    ["networkx"]="==3.5"
    
    # Other dependencies
    ["MarkupSafe"]="==3.0.2"
    ["gitdb"]="==4.0.12"
    ["smmap"]="==5.0.2"
    ["iniconfig"]="==2.1.0"
    ["pluggy"]="==1.6.0"
    ["pygments"]="==2.19.2"
    ["py-cpuinfo"]="==9.0.0"
    ["coverage"]="==7.10.2"
    ["markdown-it-py"]="==3.0.0"
    ["mdurl"]="==0.1.2"
    ["authlib"]="==1.6.1"
    ["click"]="==8.2.1"
    ["dparse"]="==0.6.4"
    ["filelock"]="==3.16.1"
    ["marshmallow"]="==4.0.0"
    ["nltk"]="==3.9.1"
    ["pydantic"]="==2.9.2"
    ["pydantic-core"]="==2.23.4"
    ["annotated-types"]="==0.7.0"
    ["ruamel.yaml"]="==0.18.14"
    ["ruamel.yaml.clib"]="==0.2.12"
    ["safety-schemas"]="==0.0.14"
    ["tenacity"]="==9.1.2"
    ["tomlkit"]="==0.13.3"
    ["regex"]="==2025.7.34"
    ["tqdm"]="==4.67.1"
    ["joblib"]="==1.5.1"
    ["sympy"]="==1.14.0"
    ["fsspec"]="==2025.7.0"
    ["jsonschema"]="==4.25.0"
    ["Cython"]="==3.1.2"
    ["pybind11"]="==3.0.0"
)

# Function to update dependencies in a pyproject.toml file
update_pyproject_dependencies() {
    local file="$1"
    local temp_file=$(mktemp)
    
    echo "Updating dependencies in: $file"
    
    # Read the file and update dependency versions
    python3 -c "
import sys
import re
import tomllib
import toml

file_path = '$file'
temp_file = '$temp_file'

# Read the current pyproject.toml
with open(file_path, 'r') as f:
    content = f.read()

# Dictionary of pinned versions
pinned = {
$(for pkg in "${!PINNED_VERSIONS[@]}"; do
    echo "    '$pkg': '${PINNED_VERSIONS[$pkg]}',"
done)
}

# Function to replace dependency versions
def update_dependency_line(line):
    # Match dependency patterns like 'package>=1.0.0' or 'package'
    match = re.match(r'^(\s*[\"\\']?)([a-zA-Z0-9_.-]+)(\[.*?\])?([><=!~,\s0-9.]*)(.*?)([\"\\']?)(\s*,?\s*)$', line.strip())
    if match:
        indent, pkg_name, extras, version_spec, rest, quote_end, trailing = match.groups()
        
        # Normalize package name (replace underscores with hyphens for lookup)
        lookup_name = pkg_name.replace('_', '-')
        
        if lookup_name in pinned or pkg_name in pinned:
            # Use the pinned version
            pinned_version = pinned.get(lookup_name, pinned.get(pkg_name, ''))
            extras_part = extras or ''
            new_line = f'{indent}\"{pkg_name}{extras_part}{pinned_version}\",{trailing}'
            return new_line
    
    return line

# Split content into lines and update dependency sections
lines = content.split('\\n')
in_dependencies = False
in_optional_deps = False
updated_lines = []

for line in lines:
    # Check if we're entering dependencies section
    if line.strip() == 'dependencies = [':
        in_dependencies = True
        updated_lines.append(line)
        continue
    
    # Check if we're entering optional dependencies section  
    if '[project.optional-dependencies]' in line or line.strip().endswith('= ['):
        in_optional_deps = True
        updated_lines.append(line)
        continue
        
    # Check if we're leaving a dependencies section
    if in_dependencies and line.strip() == ']':
        in_dependencies = False
        updated_lines.append(line)
        continue
        
    if in_optional_deps and (line.strip() == ']' or (line.strip() and not line.startswith(' ') and not line.startswith('\\t'))):
        in_optional_deps = False
        updated_lines.append(line)
        continue
    
    # Update dependency lines
    if (in_dependencies or in_optional_deps) and line.strip() and not line.strip().startswith('#'):
        updated_line = update_dependency_line(line)
        updated_lines.append(updated_line)
    else:
        updated_lines.append(line)

# Write updated content
with open(temp_file, 'w') as f:
    f.write('\\n'.join(updated_lines))
"

    # Replace the original file with the updated one
    mv "$temp_file" "$file"
    echo "Updated: $file"
}

# Find and update all pyproject.toml files
echo "Finding all pyproject.toml files..."
find packages/ -name "pyproject.toml" -type f | while read -r file; do
    update_pyproject_dependencies "$file"
done

echo "=== All SAGE package dependencies have been updated with pinned versions ==="
echo "This should significantly speed up 'pip install sage' by avoiding dependency backtracking."
