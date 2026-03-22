# SAGE Repo Infrastructure Templates

This directory provides standardised scaffolding for all SAGE split-repos. Apply the templates to a
new (or existing) repo with a single command.

For the 2026 consolidation direction, do **not** use these templates to create new core-layer repos
that duplicate `sage.foundation`, `sage.stream`, `sage.runtime`, or `sage.serving`. They should be
used only for clearly independent optional adapters, benchmark utilities, or other genuinely
separate deliverables.

## Quick start

```bash
cd /path/to/target-repo
/path/to/SAGE/tools/templates/init-repo.sh \
    --pkg-name isage-rag \
    --pkg-mod  sage_rag \
    --desc     "SAGE RAG components"
```

Pass `--cpp` for repos that contain a C++ extension (for example, independently owned
high-performance adapters):

```bash
init-repo.sh --pkg-name isage-anns --pkg-mod sage_anns --cpp
```

Options:

| Flag               | Description                               |
| ------------------ | ----------------------------------------- |
| `--pkg-name NAME`  | PyPI package name (e.g. `isage-rag`)      |
| `--pkg-mod MODULE` | Python import name (e.g. `sage_rag`)      |
| `--desc TEXT`      | Short one-line description                |
| `--cpp`            | Also apply C++ extension skeleton         |
| `--dry-run`        | Show what would be copied without writing |
| `--force`          | Overwrite existing files                  |

______________________________________________________________________

## Directory structure

```text
tools/templates/
├── init-repo.sh              ← one-command initialiser
│
├── new-repo/                 ← Python-only template
│   ├── hooks/
│   │   ├── pre-commit        ← delegates to pre-commit framework
│   │   ├── post-commit       ← auto-bump BUILD digit in _version.py
│   │   └── pre-push          ← ruff check + pytest + main-branch guard
│   ├── .github/
│   │   └── workflows/
│   │       ├── ci.yml                  ← ruff + pytest on push/PR
│   │       ├── release.yml             ← publish to PyPI + dispatch downstream
│   │       ├── update-deps.yml         ← receive upstream release, auto-PR bump
│   │       ├── version-source-guard.yml ← validate _version.py is sole source
│   │       └── back-sync.yml           ← main → main-dev auto PR
│   ├── src/my_pkg/
│   │   ├── _version.py       ← version source of truth
│   │   └── __init__.py
│   ├── .pre-commit-config.yaml
│   ├── codecov.yml
│   ├── pyproject.toml        ← dynamic version, dev extras
│   ├── pytest.ini
│   ├── quickstart.sh         ← environment check + hooks install + pip install -e .[dev]
│   └── ruff.toml
│
└── new-repo-cpp/             ← extra files for C++ extension repos
    ├── CMakeLists.txt        ← scikit-build-core + pybind11
    ├── csrc/
    │   └── bindings.cpp      ← PYBIND11_MODULE entry point
    ├── pyproject.toml        ← scikit-build-core backend
    ├── build_manylinux.sh    ← manylinux2014 wheel builder (Docker)
    └── .github/
        └── workflows/
            └── release.yml   ← cibuildwheel → PyPI
```

______________________________________________________________________

## Hook behaviour

| Hook          | Trigger            | What it does                                                                |
| ------------- | ------------------ | --------------------------------------------------------------------------- |
| `pre-commit`  | `git commit`       | Runs all checks in `.pre-commit-config.yaml` (ruff, trailing-whitespace, …) |
| `post-commit` | after `git commit` | Bumps `_version.py` BUILD digit (X.Y.Z → X.Y.Z.1) and amends the commit     |
| `pre-push`    | `git push`         | Blocks push to `main`; runs `ruff check` + `pytest -x -q`                   |

Set `SAGE_SKIP_VERSION_BUMP=1` to disable the post-commit version bump (e.g. in CI).

______________________________________________________________________

## Version source of truth

Every package must follow the unified convention enforced by `version-source-guard.yml`:

1. **Only** `src/<package>/_version.py` contains a hardcoded `__version__`.
1. `pyproject.toml` uses `dynamic = ["version"]` and points to `_version.py`.
1. `__init__.py` imports from `_version.py`; it never defines `__version__` itself.
1. To bump: edit only `_version.py` (or let the post-commit hook handle the BUILD digit).

______________________________________________________________________

## Cross-repo release pipeline

The release pipeline can create a fully automated version-linking chain for repos that still have a
real upstream/downstream release relationship.

### How it works

| Step | Who                                     | What                                                                            |
| ---- | --------------------------------------- | ------------------------------------------------------------------------------- |
| 1    | Developer                               | Tags upstream repo (`v0.2.5`)                                                   |
| 2    | `release.yml`                           | Publishes to PyPI                                                               |
| 3    | `release.yml` (dispatch_downstream job) | Sends `repository_dispatch` (event: `package-released`) to each downstream repo |
| 4    | `update-deps.yml` (downstream)          | Updates `pyproject.toml` constraint and opens a PR                              |
| 5    | Developer                               | Reviews / merges the auto-PR                                                    |

### Setup required — GitHub secret

Each repo that dispatches to downstreams must have a secret named **`DISPATCH_PAT`**:

- Type: GitHub classic PAT with **`repo`** scope (write access to all downstream repos)
- Set in: *Repo Settings → Secrets and variables → Actions → New repository secret*

### Configuring downstream repos in `release.yml`

For each upstream repo, edit `.github/workflows/release.yml` and set the `DOWNSTREAM_REPOS` variable
in the `dispatch-downstream` job:

```yaml
# Example: an independently owned base adapter notifies a dependent adapter repo
DOWNSTREAM_REPOS="intellistream/some-dependent-repo"

# Example: a leaf repo with no automatic downstream bump targets
DOWNSTREAM_REPOS=""
```

### Dependency graph

```text
independent-base-package
    └─ dependent-package
```

______________________________________________________________________

## Related issues

- #1456 — This template directory (P1 infra)
- #1459 / #1460 — historical C++ split-repo rollout examples (use `--cpp` flag when still justified)
- #1465 — Cross-repo release pipeline (release.yml dispatch + update-deps.yml)
