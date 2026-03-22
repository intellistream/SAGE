.PHONY: help install lint format test test-quick test-all quality clean clean-cache build publish check version docs build-extensions clean-env

# 默认目标：显示帮助
help:
	@echo "🚀 SAGE 开发工具快捷命令"
	@echo ""
	@echo "📦 安装与设置:"
	@echo "  make install         - 快速安装 SAGE（开发模式）"
	@echo "  make install-dev     - 按正确顺序安装所有子包（推荐用于开发）"
	@echo "  make install-deps    - 仅安装依赖"
	@echo "  make clean-env       - 运行 SAGE 卸载/清理助手"
	@echo "  make build-extensions - 构建 C++ 扩展（DB, Flow, TSDB）"
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
	@echo "  make clean-cache  - 清理构建缓存（egg-info, build, dist）"
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
	@echo "  make docs-check   - 检查文档质量"
	@echo "  make docs-report  - 生成文档质量报告"
	@echo ""
	@echo "💡 提示: 这些命令调用 'sage-dev' 工具，需要源码安装模式"

# 安装
install:
	@echo "🚀 运行快速安装..."
	./quickstart.sh

install-dev:
	@echo "🔧 开发模式安装主仓（editable）..."
	@python3 -m pip install -e '.[dev]'
	@echo "✅ 主仓开发安装完成！"
	@echo ""
	@echo "ℹ️  Main repo now ships foundation/stream/runtime/serving/cli in-tree."
	@echo "ℹ️  Additional ecosystem repos remain independently released when needed."
	@echo ""
	@echo "📊 验证版本一致性..."
	@pip list | grep -E "^isage"

install-deps:
	@echo "📦 安装依赖..."
	pip install -r requirements.txt || true

# C++ 扩展构建
build-extensions:
	@echo "🔨 构建 C++ 扩展..."
	@echo "ℹ️ TSDB 已迁移为独立包（isage-tsdb），不再在 SAGE 内部构建。"
	@echo "✅ 本仓库无需执行 TSDB 本地扩展构建。"

# 代码质量
lint:
	@echo "🔍 运行代码检查..."
	sage-dev quality --check-only

format:
	@echo "✨ 格式化代码..."
	sage-dev quality

quality:
	@echo "🎨 运行完整质量检查..."
	sage-dev quality

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
	sage-dev package pypi build

clean:
	@echo "🧹 清理构建产物..."
	@echo "  • 清理 Python 包构建产物..."
	@find packages -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find packages -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find packages -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@echo "  • 清理 C++ 扩展构建产物..."
	@rm -rf .sage/build/*
	@echo "  • 清理测试和覆盖率产物..."
	@rm -rf .sage/htmlcov/ .sage/cache/pytest/ .sage/cache/mypy/ .sage/cache/ruff/
	@echo "  • 清理旧的构建目录（已废弃）..."
	@rm -rf build/ htmlcov/
	@find packages -type d \( -name "lib" -o -name "bin" -o -name "install" \) -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 清理完成"

clean-cache:
	@echo "🧹 清理构建缓存..."
	@bash tools/install/fixes/build_cache_cleaner.sh clean
	@echo "✅ 缓存清理完成"

clean-env:
	@echo "🧹 运行 SAGE 卸载与环境清理工具..."
	./manage.sh clean-env
	@echo "✅ 清理完成"

check:
	@echo "🔍 检查包配置..."
	sage-dev pypi check

publish:
	@echo "📦 发布到 TestPyPI..."
	sage-dev pypi publish --dry-run

publish-prod:
	@echo "📦 发布到生产 PyPI..."
	@sage-dev pypi publish

# 版本管理
version:
	@sage-dev version list

version-bump:
	@sage-dev version bump

# 文档
docs:
	@echo "📚 SAGE meta 仓库当前仅维护仓库内文档检查流程"
	@bash tools/maintenance/check_docs.sh

docs-serve:
	@echo "🌐 SAGE meta 仓库当前没有内置文档站点可启动"
	@echo "请直接查看 docs/、README.md 和各独立仓库文档"

docs-check:
	@echo "🔍 检查文档质量..."
	@bash tools/maintenance/check_docs.sh

docs-report:
	@echo "📊 生成文档质量报告..."
	@bash tools/maintenance/check_docs.sh
