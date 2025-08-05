# SAGE Project Makefile
# 已集成构建和安装问题修复

.PHONY: build install install-prod all help clean dev-install commercial-install

# Development install (editable mode) - 推荐给开发者使用
dev-install:
	@echo "🛠️  Installing SAGE in development mode (开源版本)..."
	@echo "📦 Installing open source packages: kernel, middleware, userspace, tools..."
	pip install -r requirements-dev.txt
	@echo "✅ Development installation complete!"
	@echo "💡 Code changes will take effect immediately (except C++ extensions)"
	@echo "🎯 已安装的包: sage-kernel, sage-middleware, sage-userspace, sage-cli, sage-dev-toolkit"

# Commercial install (editable mode) - 仅供内部开发者使用
commercial-install:
	@if [ ! -f requirements-commercial.txt ]; then \
		echo "❌ Commercial requirements file not found!"; \
		echo "🔒 This installation requires access to commercial packages."; \
		exit 1; \
	fi
	@echo "🏢 Installing SAGE Commercial Edition (闭源版本)..."
	@echo "📦 Installing commercial packages with enhanced features..."
	pip install -r requirements-commercial.txt
	@echo "✅ Commercial installation complete!"
	@echo "💡 Code changes will take effect immediately"
	@echo "🎯 已安装的包: sage-kernel-commercial, sage-middleware-commercial, sage-userspace-commercial"

# Build all wheels using the fixed build script
build:
	@echo "🔨 Building all wheels (with integrated fixes)..."
	mkdir -p ~/.sage/makefile_logs
	./scripts/build_all_wheels.sh > ~/.sage/makefile_logs/build.log 2>&1

# Install all wheels using the fixed install script (production install)
install:
	@echo "📦 Installing wheels to site-packages (production mode)..."
	mkdir -p ~/.sage/makefile_logs
	./scripts/install_wheels.sh > ~/.sage/makefile_logs/install.log 2>&1

# Alias for production install
install-prod: install

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
	@echo "  dev-install        - Install SAGE开源版 in development mode (editable, recommended)"
	@echo "  commercial-install - Install SAGE商业版 in development mode (内部使用)"
	@echo "  build              - Build all wheels (with outlines_core/xformers fixes)"
	@echo "  install            - Install wheels (with dependency resolution fixes)"
	@echo "  all                - Build and install in one command"
	@echo "  clean              - Clean all build artifacts"
	@echo "  help               - Show this help message"
	@echo ""
	@echo "🚀 Quick start for developers:"
	@echo "   make dev-install        # 开源版一键安装(kernel+middleware+userspace+tools)"
	@echo "   make commercial-install # 商业版一键安装(需要商业授权)"
	@echo ""
	@echo "📦 开源版包含:"
	@echo "  ✅ sage-kernel (核心内核)"
	@echo "  ✅ sage-middleware (中间件)"
	@echo "  ✅ sage-userspace (用户空间)"
	@echo "  ✅ sage-cli (命令行工具)"
	@echo "  ✅ sage-dev-toolkit (开发工具)"
	@echo ""
	@echo "🏢 商业版额外包含:"
	@echo "  ⭐ sage-kernel-commercial (高性能队列, 企业级功能)"
	@echo "  ⭐ sage-middleware-commercial (数据库连接器, 存储中间件)"
	@echo "  ⭐ sage-userspace-commercial (企业用户空间)"
	@echo ""
	@echo "🔧 Integrated fixes:"
	@echo "  ✅ outlines_core build failure fix"
	@echo "  ✅ xformers PEP517 deprecation warning fix"
	@echo "  ✅ Rust environment auto-setup"
	@echo "  ✅ Binary package preference"