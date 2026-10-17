#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MANIFEST="$SAGE_ROOT/tools/install/satellite-repositories.json"

source "$SAGE_ROOT/tools/install/installers/clone_satellite_repos.sh"

repos="$(load_public_repos_from_manifest "$MANIFEST")"
repo_count="$(printf '%s\n' "$repos" | sed '/^$/d' | wc -l | tr -d ' ')"

if [ "$repo_count" -ne 11 ]; then
    echo "Expected 11 default public repositories, found $repo_count" >&2
    exit 1
fi

if printf '%s\n' "$repos" | grep -q 'github.com/intellistream'; then
    echo "Public SAGE repository manifest contains an IntelliStream URL" >&2
    exit 1
fi

if printf '%s\n' "$repos" | grep -qE 'neuromem|FlowRAG|private-materials'; then
    echo "Public SAGE repository manifest contains a private repository" >&2
    exit 1
fi

for expected in \
    "SAGE-Docs|https://github.com/RIDE-Lab/SAGE-Docs.git" \
    "sage-examples|https://github.com/RIDE-Lab/sage-examples.git" \
    "sage-rag|https://github.com/RIDE-Lab/sage-rag.git" \
    "sage-studio|https://github.com/RIDE-Lab/sage-studio.git"
do
    if ! printf '%s\n' "$repos" | grep -Fxq "$expected"; then
        echo "Missing canonical repository entry: $expected" >&2
        exit 1
    fi
done

echo "Satellite repository manifest checks passed"
