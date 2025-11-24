# Dependency Management and Packaging Optimization

This document outlines the strategies used in SAGE to optimize dependency management and packaging,
aiming to improve user installation experience, compatibility, and maintainability.

## 1. Dependency Versioning Strategy

To enhance compatibility with other packages in the user's environment, we have adopted a flexible
versioning strategy for our dependencies.

### Problem

Previously, many dependencies in `pyproject.toml` were pinned to exact versions (e.g.,
`torch==2.7.1`). This approach, while ensuring deterministic builds, could lead to conflicts when
users had other packages requiring different versions of the same dependency.

### Solution

We have relaxed the version constraints to allow for a range of compatible versions. The new
strategy is as follows:

- **Use ranged versions**: Instead of pinning to an exact version, we now specify a compatible
  range. For example, `torch>=2.7.0,<3.0.0`. This allows `pip` to select a version that satisfies
  the requirements of SAGE and other installed packages.
- **Major version cap**: We cap the upper bound to the next major version (e.g., `<3.0.0`) to avoid
  pulling in potentially breaking changes from new major releases.
- **Flexible patch versions**: For most libraries, we allow patch and minor version updates, which
  are generally backward-compatible.

**Example (`packages/sage-kernel/pyproject.toml`):**

```toml
# Before
torch==2.7.1

# After
torch>=2.7.0,<3.0.0
```

This change significantly reduces the likelihood of dependency conflicts during installation.

## 2. Optional Dependencies and `extras`

SAGE is a modular framework, and not all users require all of its features. To cater to different
use cases, we have structured our dependencies into `extras`.

### Problem

A monolithic dependency list forces users to install packages they may not need (e.g., GPU-specific
libraries on a CPU-only machine), leading to bloated environments and longer installation times.

### Solution

We have defined several `extras` that allow users to install only the components they need.

**Key `extras` in `isage-kernel`:**

- `[gpu]`: Installs dependencies required for GPU acceleration. This is the default for `torch`.
- `[cpu]`: Ensures that CPU-only versions of libraries are used where applicable.
- `[web]`: Installs packages for web-based functionalities (e.g., `fastapi`, `uvicorn`).
- `[monitoring]`: Adds support for monitoring tools.

**Installation Examples:**

- **Minimal CPU installation:**

  ```bash
  pip install isage-kernel[cpu]
  ```

- **GPU installation with web support:**

  ```bash
  pip install isage-kernel[gpu,web]
  ```

This approach provides a more tailored and efficient installation experience.

## 3. Pre-compiled Wheels for C++ Extensions

Some SAGE components, like `sage-middleware`, include C++ extensions for performance-critical
operations. Compiling these extensions on the user's machine can be slow and error-prone, especially
if build tools (like a C++ compiler and CMake) are not pre-installed.

### Problem

- **Slow installation**: Source distributions (`sdist`) require local compilation, which can take
  several minutes.
- **Compilation errors**: Users may lack the necessary build toolchain, leading to installation
  failures.
- **Inconsistent environments**: Differences in local build environments can lead to subtle bugs.

### Solution

We pre-compile binary wheels for our C++ extensions for a variety of common platforms (Linux, macOS,
Windows) and Python versions (3.10, 3.11, 3.12).

We use `cibuildwheel` in our GitHub Actions workflow (`.github/workflows/build-wheels.yml`) to
automate this process. When a new version of SAGE is released, this workflow builds the wheels and
uploads them to PyPI alongside the source distribution.

**Benefits:**

- **Faster installation**: `pip` will automatically download and install the appropriate
  pre-compiled wheel, skipping the local compilation step entirely. This reduces installation time
  from minutes to seconds.
- **Improved reliability**: Since no local compilation is needed, the risk of installation failure
  due to missing build tools is eliminated.
- **Consistency**: All users get the same compiled binary, ensuring consistent behavior across
  different machines.

When a user runs `pip install isage-middleware`, `pip` intelligently selects the compatible wheel
for their system. If a pre-compiled wheel is not available for their specific platform (e.g., a less
common Linux distribution), `pip` falls back to downloading the source distribution (`sdist`) and
compiling it locally, ensuring that the package can still be installed.
