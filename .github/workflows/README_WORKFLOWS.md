# Workflow Inventory (Main-Only)

This repository uses a main-only branch policy.

## Policy

- Default branch: main
- Large features: develop on feature/* and merge via PR to main
- No main-dev workflow is supported

## Trigger Convention

- Pull requests target main
- Push events are tracked on main
- Manual workflows use workflow_dispatch

Keep workflow branch filters aligned with this policy.
