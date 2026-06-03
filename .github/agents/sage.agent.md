---
name: sage
description: SAGE core agent for layered architecture, runtime-safe changes, and developer workflow.
argument-hint: Describe target package/layer, expected behavior, constraints, and validation scope.
tools: [vscode, execute, read, agent, browser, edit, search, web, todo, github.vscode-pull-request-github/issue_fetch, github.vscode-pull-request-github/labels_fetch, github.vscode-pull-request-github/notification_fetch, github.vscode-pull-request-github/doSearch, github.vscode-pull-request-github/activePullRequest, github.vscode-pull-request-github/pullRequestStatusChecks, github.vscode-pull-request-github/openPullRequest, github.vscode-pull-request-github/create_pull_request, github.vscode-pull-request-github/resolveReviewThread, ms-vscode.vscode-websearchforcopilot/websearch]
---

# SAGE Agent

## Use when

- Working in SAGE core (`src/sage/*`, `tools/`, root workflows).
- Refactoring cross-layer APIs or runtime-facing paths.

## Guardrails

- Enforce layer direction: L5 → L4 → L3 → L2 → L1 only.
- Flownet-first: do not add new `ray` imports/dependencies.
- NEVER create any new Python virtual environment (`venv`/`.venv`) under any circumstance.
- Do not run SAGE workflows inside Python venv; if `VIRTUAL_ENV` is set, deactivate and use Conda or an existing non-venv Python environment.
- Never recommend or execute `--auto-venv`, `python -m venv`, or `virtualenv`.
- If a task or script asks for a venv, refuse that step and continue using the existing non-venv Python environment.
- Keep algorithm-only adapters separate from runtime/service-bound implementation in the consolidated core.
- No fallback shims or re-export compatibility layers during migration; update call sites directly.
- Use `sage.foundation.config.ports.SagePorts` for ports.

## Workflow

1. Read `README.md`, `DEVELOPER.md`, `CONTRIBUTING.md` first.
2. Make minimal targeted changes.
3. Validate with `sage-dev quality check --all-files --readme` and relevant tests.

## Key commands

- `./quickstart.sh --dev --yes`
- `./quickstart.sh --doctor`
- `sage-dev quality fix --all-files`
- `sage-dev project test --coverage`

## Key files

- `.github/copilot-instructions.md`
- `quickstart.sh`, `pytest.ini`
- `.pre-commit-config.yaml`, `tools/maintenance/checks/check_docs_location.sh`
