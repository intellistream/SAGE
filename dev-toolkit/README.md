# SAGE Development Toolkit

🛠️ **Unified development tools for the SAGE project**

The SAGE Development Toolkit integrates all development utilities into a single, powerful command-line interface with rich terminal output, intelligent automation, and comprehensive reporting.

## 🚀 Quick Start

```bash
# Install the toolkit
pip install -e dev-toolkit/

# Show all available commands  
sage-dev --help

# Check status and configuration
sage-dev status
```

## 📋 Available Commands

### Core Commands
- **`sage-dev test`** - Intelligent test execution with parallel support
- **`sage-dev analyze`** - Comprehensive dependency analysis
- **`sage-dev package`** - Package management across SAGE ecosystem  
- **`sage-dev report`** - Generate development reports

### Development Tools
- **`sage-dev fix-imports`** - Fix import paths automatically
- **`sage-dev update-vscode`** - Update VS Code Python configurations
- **`sage-dev setup-test`** - One-click environment setup and testing
- **`sage-dev list-tests`** - List all available tests

### Utility Commands
- **`sage-dev status`** - Show toolkit status and configuration
- **`sage-dev version`** - Show version information

## 💡 Usage Examples

```bash
# Run tests on changed files (intelligent diff-based testing)
sage-dev test --mode diff --workers 4

# Run all tests for a specific package
sage-dev test --mode package --package sage-core

# Fix import paths (dry run to see what would change)
sage-dev fix-imports --dry-run

# Update VS Code Python paths with verbose output
sage-dev update-vscode --mode enhanced --verbose

# Analyze dependencies and detect circular imports
sage-dev analyze --type circular

# List all SAGE packages with status
sage-dev package list

# Run complete environment setup and test cycle
sage-dev setup-test --workers 8 --quick-test

# Generate comprehensive development report  
sage-dev report --output-format both
```

## 🎯 Key Features

### 🔬 **Intelligent Testing**
- **Diff-based testing**: Only run tests affected by your changes
- **Parallel execution**: Leverage multiple CPU cores for faster testing
- **Rich reporting**: Beautiful terminal output with detailed results
- **Multiple modes**: `all`, `diff`, `package` testing modes

### 📦 **Package Management**  
- **Dependency resolution**: Automatic dependency order installation
- **Status monitoring**: Check package installation and health
- **Build automation**: Build and distribute SAGE packages
- **Circular dependency detection**: Prevent import cycles

### 🔧 **Development Automation**
- **Import path fixing**: Automatically fix broken import statements
- **VS Code integration**: Update Python paths for better IntelliSense
- **One-click setup**: Complete environment setup with single command
- **Rich terminal output**: Beautiful tables, progress bars, and colored output

### 📊 **Comprehensive Reporting**
- **Multi-format output**: JSON, Markdown, and terminal-friendly reports
- **Execution tracking**: Detailed timing and performance metrics
- **Error analysis**: Clear error messages with suggested fixes
- **Historical data**: Track changes over time

## 🏗️ Architecture

```
dev-toolkit/
├── src/sage_dev_toolkit/
│   ├── core/           # Core framework (config, exceptions, toolkit)
│   ├── cli/            # Command-line interface (Typer-based)
│   ├── tools/          # Integrated development tools
│   └── utils/          # Utility functions and helpers
├── config/             # Configuration templates and defaults
├── templates/          # Report templates (Jinja2)
├── tests/              # Test suite for the toolkit
└── docs/               # Documentation and guides
```

## ⚙️ Configuration

The toolkit uses YAML-based configuration with environment support:

```yaml
# config/default.yaml
project_root: "/path/to/SAGE" 
environment: "development"

tools:
  test_runner:
    enabled: true
    max_workers: 4
    timeout: 300
  
  package_manager:
    enabled: true
    
  dependency_analyzer:
    enabled: true
```

Environment-specific overrides:
- `config/development.yaml`
- `config/production.yaml` 
- `config/ci.yaml`

## 🔄 Migration from Old Scripts

The toolkit replaces several standalone scripts with enhanced versions:

| **Old Script** | **New Command** | **Enhancements** |
|----------------|-----------------|------------------|
| `fix_import_paths.py` | `sage-dev fix-imports` | ✅ Dry-run mode, better patterns |
| `one_click_setup_and_test.py` | `sage-dev setup-test` | ✅ Parallel testing, rich output |
| `update_vscode_paths.py` | `sage-dev update-vscode` | ✅ Enhanced mode, verbose output |
| `sage-package-manager.py` | `sage-dev package` | ✅ Dependency resolution, status |
| `test_runner.py` | `sage-dev test` | ✅ Multiple modes, parallel execution |
| `advanced_dependency_analyzer.py` | `sage-dev analyze` | ✅ Circular detection, reporting |

All original scripts are archived in `archive/tools/` and `archive/scripts/`.

## 🎨 Rich Terminal Experience

The toolkit provides a modern CLI experience with:

- 🎨 **Colored output** with semantic highlighting
- 📋 **Rich tables** for structured data display
- 📊 **Progress bars** for long-running operations
- 🔍 **Detailed help** system with examples
- ⚡ **Fast execution** with parallel processing
- 📝 **Comprehensive logging** with multiple levels

## 🤝 Contributing

To extend the toolkit:

1. **Add new tools** in `src/sage_dev_toolkit/tools/`
2. **Update CLI** in `src/sage_dev_toolkit/cli/main.py`
3. **Add configuration** in `config/default.yaml`
4. **Write tests** in `tests/`
5. **Update documentation** in this README

## 📞 Support

- **Documentation**: Check command help with `sage-dev <command> --help`
- **Status**: Run `sage-dev status` to diagnose issues
- **Logs**: Check `dev_reports/` for detailed execution logs
- **Migration**: See `archive/MIGRATION_SUMMARY.md` for script migration guide

---

**🛠️ Built with:** Python 3.10+, Typer, Rich, PyYAML, Jinja2  
**📦 Maintained by:** IntelliStream SAGE Team  
**🔗 Repository:** https://github.com/intellistream/SAGE
