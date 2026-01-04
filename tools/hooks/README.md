# SAGE Git Hooks

This directory contains Git hook templates for SAGE development workflows.

## Available Hooks

### post-commit.sample - Auto PyPI Publisher

Automatically publishes affected packages to PyPI after each commit.

**Features**:

- 🔍 Detects modified packages automatically
- 📦 Publishes to PyPI with version auto-increment
- 🧪 Optional TestPyPI validation before production
- 🔒 Branch and confirmation controls
- ⚙️ Fully configurable

**Installation**:

```bash
# Copy to .git/hooks/
cp tools/hooks/post-commit.sample .git/hooks/post-commit
chmod +x .git/hooks/post-commit

# Clone sage-pypi-publisher if not already done
git clone https://github.com/intellistream/sage-pypi-publisher.git ~/sage-pypi-publisher
```

**Configuration**:

Edit `.git/hooks/post-commit` and configure these variables:

```bash
# Publisher path
PUBLISHER_PATH="${HOME}/sage-pypi-publisher"

# Enable/disable auto-publish
AUTO_PUBLISH_ENABLED=false  # Set to true to enable

# Branch restriction (empty = all branches)
AUTO_PUBLISH_BRANCH="main"

# Confirmation required
REQUIRE_CONFIRMATION=true

# Version bump type: patch (0.0.1), minor (0.1.0), major (1.0.0)
VERSION_BUMP_TYPE="patch"

# Test on TestPyPI first
TEST_PYPI_FIRST=false
```

**Usage**:

Once installed and configured, the hook runs automatically after `git commit`:

```bash
git add packages/sage-common/...
git commit -m "feat(common): add new feature"

# Hook automatically detects sage-common was modified
# and publishes it to PyPI after confirmation
```

**Manual Publishing** (without hook):

```bash
cd ~/sage-pypi-publisher
./publish.sh sage-common --auto-bump patch
```

## Configuration Examples

### Development Workflow (Recommended)

```bash
AUTO_PUBLISH_ENABLED=false       # Manual control
REQUIRE_CONFIRMATION=true        # Always confirm
TEST_PYPI_FIRST=true            # Test first
```

### CI/CD Automation

```bash
AUTO_PUBLISH_ENABLED=true        # Auto-publish
AUTO_PUBLISH_BRANCH="main"       # Only on main
REQUIRE_CONFIRMATION=false       # No confirmation needed
TEST_PYPI_FIRST=false           # Direct to PyPI
```

### Conservative Approach

```bash
AUTO_PUBLISH_ENABLED=true        # Enable hook
AUTO_PUBLISH_BRANCH="release"    # Only on release branch
REQUIRE_CONFIRMATION=true        # Always ask
TEST_PYPI_FIRST=true            # Always test first
VERSION_BUMP_TYPE="patch"        # Small increments
```

## Troubleshooting

**Hook not running?**

- Check permissions: `ls -la .git/hooks/post-commit`
- Should be executable: `chmod +x .git/hooks/post-commit`
- Check branch restrictions in configuration

**Publisher not found?**

- Clone it:
  `git clone https://github.com/intellistream/sage-pypi-publisher.git ~/sage-pypi-publisher`
- Update `PUBLISHER_PATH` in hook if using different location

**Publishing fails?**

- Check PyPI credentials: `~/.pypirc`
- Verify package version in `_version.py`
- Check publisher logs for detailed error messages

## Disabling Hooks

To temporarily disable the hook:

```bash
# Rename it
mv .git/hooks/post-commit .git/hooks/post-commit.disabled

# Or set AUTO_PUBLISH_ENABLED=false in the hook
```

## See Also

- [sage-pypi-publisher](https://github.com/intellistream/sage-pypi-publisher) - Standalone
  publishing tool
- [PyPI Publishing Guide](/.github/copilot-instructions.md#pypi-publishing) - Copilot instructions
- [CONTRIBUTING.md](/CONTRIBUTING.md) - General contribution guidelines
