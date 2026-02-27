#!/usr/bin/env bash
# build_manylinux.sh — Build manylinux2014 wheels for the C++ extension
#
# Usage:
#   ./build_manylinux.sh                   # build for Python 3.11 (default)
#   PYTHON_VERSION=3.12 ./build_manylinux.sh
#
# Output: dist/*.whl  (manylinux2014_x86_64)
#
# Requires: Docker (or podman)

set -euo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
IMAGE="quay.io/pypa/manylinux2014_x86_64"
PYTHON_TAG="cp${PYTHON_VERSION//./}-cp${PYTHON_VERSION//./}"

echo "Building manylinux2014 wheel for Python ${PYTHON_VERSION}..."
echo "Image: ${IMAGE}"
echo ""

docker run --rm \
    -v "$(pwd)":/project \
    -w /project \
    "${IMAGE}" \
    bash -c "
        set -e
        PYBIN=/opt/python/${PYTHON_TAG}/bin
        \${PYBIN}/pip install --upgrade pip scikit-build-core pybind11
        \${PYBIN}/pip wheel . -w /tmp/wheelhouse --no-deps
        auditwheel repair /tmp/wheelhouse/*.whl -w dist/
        echo 'Wheels in dist/:'
        ls dist/
    "

echo ""
echo "Done. Wheel(s) in dist/"
