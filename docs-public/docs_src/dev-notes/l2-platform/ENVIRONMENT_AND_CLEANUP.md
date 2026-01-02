# Environment isolation and cleanup

This short guide documents SAGE's environment isolation features and cleanup utilities.

## Virtual environment guidance

- SAGE strongly recommends installing inside a virtual environment (Conda or `venv`).
- The installer (`quickstart.sh`) will detect if you are running inside a virtual environment.
- Control behavior with the environment variable `SAGE_VENV_POLICY`:
  - `warning` (default) — show a warning and let the user continue or cancel.
  - `error` — refuse to install outside a virtual environment.
  - `ignore` — skip the check.

### Automatic creation

- Use `./quickstart.sh --auto-venv` to request automatic virtual environment creation.
  - If `conda` is available, the installer will prefer Conda and create a `sage` environment.
  - Otherwise the installer will create a `venv` at `.sage/venv` and activate it for the install.
  - If the plain `python3 -m venv` command can’t run (missing `ensurepip`), the installer now
    attempts to install `virtualenv` into your user site with
    `pip install --user --break-system-packages virtualenv` before creating `.sage/venv`. If that
    also fails under strict PEP 668 policies, install the `python3-venv` package
    (`sudo apt install python3.12-venv` on Debian/Ubuntu) or create the venv manually before
    rerunning `--auto-venv`.

Example:

```bash
./quickstart.sh --auto-venv --dev --yes
```

## Tracking installed packages

SAGE records what it installed to make uninstalling safe and reliable.

Files written under your project root `.sage/`:

- `.sage/installed_packages.txt` — list of SAGE-related pip packages recorded after install
- `.sage/install_info.json` — metadata including timestamp, install mode, venv/conda info

You can inspect these with:

```bash
bash tools/cleanup/track_install.sh show
bash tools/cleanup/track_install.sh info
```

## Uninstall & cleanup

Use the interactive uninstall helper to remove installed packages and optional virtual environments:

```bash
# Interactive uninstall (confirm prompts)
bash tools/cleanup/uninstall_sage.sh

# Skip confirmations for automation
bash tools/cleanup/uninstall_sage.sh --yes

# Or via the convenience manage.sh command
./manage.sh clean-env
# or
./manage.sh uninstall
```

What it does:

- Uninstall SAGE Python packages listed in `.sage/installed_packages.txt` (if present).
- Falls back to `tools/install/examination_tools/sage_check.sh` if the list is missing.
- Optionally deletes `.sage/venv` or the recorded Conda environment name.
- Leaves repository source and Git history intact.

## Notes and safety

- Always review `.sage/install_info.json` and `.sage/installed_packages.txt` before deleting
  environments.
- The uninstall helper will ask for confirmation before removing files or environments.
- If you prefer a manual clean, you can remove the venv directory and uninstall packages manually.

If you'd like, I can add a `make clean-env` Makefile target or wire this helper into CI cleanup
scripts.
