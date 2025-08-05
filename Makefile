# SAGE Project Makefile
# 已集成构建和安装问题修复

.PHONY: build install all help clean dev-install

# Development install (editable mode) - 推荐给开发者使用
dev-install:
	@echo "🛠️  Installing SAGE in development mode (editable)..."
	pip install -r requirements-dev.txt
	@echo "✅ Development installation complete!"
	@echo "💡 Code changes will take effect immediately (except C++ extensions)"

# Build all wheels using the fixed build script
build:
	@echo "🔨 Building all wheels (with integrated fixes)..."
	mkdir -p ~/.sage/makefile_logs
	./scripts/build_all_wheels.sh > ~/.sage/makefile_logs/build.log 2>&1

# Install all wheels using the fixed install script
install:
	@echo "📦 Installing wheels (with integrated fixes)..."
	mkdir -p ~/.sage/makefile_logs
	./scripts/install_wheels.sh > ~/.sage/makefile_logs/install.log 2>&1

# Build and install in one command
all:
	@echo "🚀 Building and installing SAGE (with integrated fixes)..."
	mkdir -p ~/.sage/makefile_logs
	./build_and_install.sh > ~/.sage/makefile_logs/all.log 2>&1

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/wheels/
	rm -rf dist/
	rm -rf ~/.sage/makefile_logs/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Show help information
help:
	@echo "Available targets:"
	@echo "  dev-install - Install in development mode (editable, recommended for devs)"
	@echo "  build       - Build all wheels (with outlines_core/xformers fixes)"
	@echo "  install     - Install wheels (with dependency resolution fixes)"
	@echo "  all         - Build and install in one command"
	@echo "  clean       - Clean all build artifacts"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "🚀 Quick start for developers:"
	@echo "   make dev-install  # Editable install, code changes take effect immediately"
	@echo ""
	@echo "🔧 Integrated fixes:"
	@echo "  ✅ outlines_core build failure fix"
	@echo "  ✅ xformers PEP517 deprecation warning fix"
	@echo "  ✅ Rust environment auto-setup"
	@echo "  ✅ Binary package preference"