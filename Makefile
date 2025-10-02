.PHONY: help install lint format test test-quick test-all quality clean build publish check version docs

# 默认目标：显示帮助
help:
	@echo "🚀 SAGE 开发工具快捷命令"
	@echo ""
	@echo "📦 安装与设置:"
	@echo "  make install      - 快速安装 SAGE（开发模式）"
	@echo "  make install-deps - 仅安装依赖"
	@echo ""
	@echo "✨ 代码质量:"
	@echo "  make lint         - 运行代码检查（flake8）"
	@echo "  make format       - 格式化代码（black + isort）"
	@echo "  make quality      - 运行完整质量检查（lint + format）"
	@echo ""
	@echo "🧪 测试:"
	@echo "  make test         - 运行所有测试"
	@echo "  make test-quick   - 运行快速测试（不包括慢速测试）"
	@echo "  make test-all     - 运行完整测试套件"
	@echo ""
	@echo "📦 构建与发布:"
	@echo "  make build        - 构建所有包"
	@echo "  make clean        - 清理构建产物"
	@echo "  make check        - 检查包配置"
	@echo "  make publish      - 发布到 TestPyPI"
	@echo "  make publish-prod - 发布到生产 PyPI（谨慎使用）"
	@echo ""
	@echo "🔧 版本管理:"
	@echo "  make version      - 显示当前版本"
	@echo "  make version-bump - 升级版本号"
	@echo ""
	@echo "📚 文档:"
	@echo "  make docs         - 构建文档"
	@echo "  make docs-serve   - 本地预览文档"
	@echo ""
	@echo "💡 提示: 这些命令调用 'sage dev' 工具，需要源码安装模式"

# 安装
install:
	@echo "🚀 运行快速安装..."
	./quickstart.sh

install-deps:
	@echo "📦 安装依赖..."
	pip install -r requirements.txt || true

# 代码质量
lint:
	@echo "🔍 运行代码检查..."
	sage dev quality --check-only

format:
	@echo "✨ 格式化代码..."
	sage dev quality

quality:
	@echo "🎨 运行完整质量检查..."
	sage dev quality

# 测试
test:
	@echo "🧪 运行测试..."
	pytest

test-quick:
	@echo "⚡ 运行快速测试..."
	pytest -m "not slow" -v

test-all:
	@echo "🧪 运行完整测试套件..."
	pytest -v --cov=packages --cov-report=html

# 构建与发布
build:
	@echo "🔨 构建所有包..."
	sage dev pypi build

clean:
	@echo "🧹 清理构建产物..."
	sage dev pypi clean

check:
	@echo "🔍 检查包配置..."
	sage dev pypi check

publish:
	@echo "📦 发布到 TestPyPI..."
	sage dev pypi publish --dry-run

publish-prod:
	@echo "⚠️  发布到生产 PyPI..."
	@read -p "确认发布到生产环境? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		sage dev pypi publish; \
	else \
		echo "已取消"; \
	fi

# 版本管理
version:
	@sage dev version list

version-bump:
	@sage dev version bump

# 文档
docs:
	@echo "📚 构建文档..."
	cd docs-public && ./build.sh

docs-serve:
	@echo "🌐 启动文档服务器..."
	cd docs-public && mkdocs serve
