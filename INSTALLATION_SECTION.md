## 🔧 Installation

SAGE now provides a modern, streamlined installation system. Choose from the following options:

### 🚀 One-Click Installation (Recommended)

```bash
# Interactive installation with guided setup
python quick_install.py

# Or directly choose installation mode:
python quick_install.py --python-only    # Python-only installation (fast)
python quick_install.py --full          # Full installation with C++ extensions
```

### 📦 Direct pip Installation

```bash
# Install from source
pip install -e .

# Or install from wheel package
pip install dist/sage_stream-*.whl
```

### 🛠️ Manual Installation

1. **Prerequisites**: Python 3.11+ required

2. **Create environment**:
   ```bash
   python -m venv sage_env
   source sage_env/bin/activate  # Linux/macOS
   # or sage_env\Scripts\activate  # Windows
   ```

3. **Install SAGE**:
   ```bash
   pip install -e .
   ```

### ✅ Verify Installation

```bash
# Check installation status
python quick_install.py --check

# Manual verification
python -c "import sage; print(f'SAGE version: {sage.__version__}')"
sage --help
```

### 🔧 For Developers

```bash
# Build wheel packages
./build_modern_wheel.sh              # Python-only wheel
./build_modern_wheel.sh --with-cpp   # With C++ extensions

# Test installation in sandbox
./test_install_sandbox.sh
```

### 📚 Detailed Installation Guide

For comprehensive installation instructions, troubleshooting, and advanced options, see [INSTALL_GUIDE.md](INSTALL_GUIDE.md).

### 🆘 Installation Issues?

1. **Python Version**: Ensure you have Python 3.11 or higher
2. **Permissions**: Use virtual environments to avoid permission issues
3. **C++ Extensions**: Install build tools if you need full performance
4. **Help**: Check our [installation guide](INSTALL_GUIDE.md) or [create an issue](https://github.com/intellistream/SAGE/issues)

---
