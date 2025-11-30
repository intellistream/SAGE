# CI 测试与覆盖率强化

**Date**: 2025-11-25  \
**Author**: SAGE Development Team  \
**Summary**: Consolidated record of the late-2025 hardening work for `sage-dev project test`, integrated coverage reporting, and CI import validation.

---

## 🎯 改动概览

- 统一所有本地与 CI 的测试入口为 `sage-dev project test --coverage`，并新增 `--coverage-report`, `--jobs`, `--timeout`, `--skip-quality-check`, `--debug` 等控制参数。
- 修复 `test_network.py`, `test_monitoring_integration.py`, `test_agent_config.py`, `test_install_modes.py`, `test_main.py` 等关键失败案例，使 `sage-common` 等包重新达到配置的覆盖率门槛。
- 在 `.github/workflows/build-test.yml` 与配套 pipelines 中替换掉手写 `pytest`，确保测试失败会终止工作流，并自动将 `.sage/coverage/{coverage.xml,htmlcov/}`、`.sage/logs/`、`.sage/reports/` 作为 artifact 上传。
- `sage-dev project test` 负责在 `.sage/coverage/` 合并 `.coverage.*` 文件并生成 term / XML / HTML 三种报告，解决覆盖率散落在根目录的问题。
- `pip-installation-test.yml` 的导入验证覆盖 `sage.benchmark`, `sage.data`, `sage.apps` 等可选组件，禁止静默跳过导入错误。

---

## 1. 统一的测试入口

`packages/sage-tools/src/sage/tools/cli/commands/dev/main.py` 中的 `project test` 子命令新增了完整的测试编排逻辑：

```bash
sage-dev project test --coverage \
  --packages sage-common,sage-kernel \
  --test-type unit \
  --coverage-report term,html,xml \
  --jobs 4 \
  --timeout 300 \
  --skip-quality-check  # 默认 True
```

关键行为：

- `_discover_all_test_files` 仅扫描目标包，排除 `.sage/`, `vendors/`, `sageLLM/` 等问题目录。
- 覆盖率数据写入 `.sage/coverage/.coverage`，并在结束后调用 `_generate_coverage_reports()` 输出三种格式。
- `--debug` 会按阶段输出时间戳和发现的测试文件，方便排查卡住的问题。

### 已修复的失败测试

| 文件 | 原因 | 修复 | 结果 |
|------|------|------|------|
| `sage/common/utils/system/test_network.py` | `pid` 作用域错误 | 初始化 `pid=None` 并兼容 `psutil.Process` mock | ✅ |
| `kernel/runtime/monitoring/test_monitoring_integration.py` | `MockEnvironment` 未实现抽象方法 | 添加空的 `submit` | ✅ |
| `libs/agents/test_agent_config.py` | 期望的路径与示例不符 | 更新断言为 `examples.tutorials...` | ✅ |
| `sage-tools/tests/pypi/test_install_modes.py` | `minimal` extras 缺失 | 补充 `project.optional-dependencies.minimal` | ✅ |
| `sage-tools/tests/test_cli/test_main.py` | Typer app 重复传入 `dev` | 直接调用 `runner.invoke(app, ["project", "status"])` | ✅ |

`sage-common` 在 83 秒内执行 12 个测试文件，覆盖率从 60% 目标提升到 67%。

---

## 2. 覆盖率报告与 Artifact

- 所有覆盖率数据集中在 `.sage/coverage/`：
  - `.coverage`：合并后的数据文件
  - `coverage.xml`：给 Codecov 使用
  - `htmlcov/`：交互式报告
- `build-test.yml` 在测试阶段结束后复制 `.sage/coverage` 到工作目录根部，便于 `actions/upload-artifact` 和 Codecov 使用。
- 失败时自动上传 `.sage/logs/` 与 `.sage/reports/` 以便复现。

本地验证：

```bash
sage-dev project test --coverage --packages sage-common --debug
ls -la .sage/coverage/
xdg-open .sage/coverage/htmlcov/index.html
```

---

## 3. GitHub Actions 行为调整

### 3.1 build-test.yml

- `pytest` shell 片段被统一替换为 `sage-dev project test --coverage --jobs 4 --timeout 300`。
- 彻底移除 `|| exit 0` 这种忽略失败的写法，测试失败立即 `exit 1`。
- 失败时附加 step：
  ```yaml
  - name: Upload Test Logs on Failure
    if: failure()
    uses: actions/upload-artifact@v4
    with:
      name: test-logs
      path: |
        .sage/logs/
        .sage/reports/
  ```
- `GITHUB_STEP_SUMMARY` 在成功时会写入覆盖率提示，指导查看 artifact。

### 3.2 pip-installation-test.yml

- 引入 `Switch Submodules to main-dev Branch` 步骤，避免 `actions/checkout` 默认的 detached HEAD 使用 `main` 分支。
- 新增导入验证逻辑：

```bash
case "${{ matrix.install-mode }}" in
  standard|full|dev)
    if pip show isage-benchmark >/dev/null; then
      python -c "import sage.benchmark" || exit 1
      python -c "from sage.data import load_qa_dataset" || exit 1
    fi
    if pip show isage-apps >/dev/null; then
      python -c "import sage.apps" || exit 1
    fi
    ;;
esac
```

- 移除 `2>/dev/null || echo "可选"` 之类静默忽略错误的做法。

---

## 4. 使用建议

1. **本地**：始终通过 `sage-dev project test --coverage` 运行测试；必要时指定 `--packages` 缩小范围。
2. **CI**：所有 workflow 若还引用旧命令（`sage-dev test` / `pytest`）应切换到新的入口以获得统一日志和 artefact 布局。
3. **故障排查**：
   - 覆盖率缺失 → 检查 `.sage/coverage/` 是否生成。
   - 测试卡住 → 使用 `--debug` 查看阶段日志。
   - pip 安装导入失败 → 在本地复现 `pip-installation-test.yml` 的导入片段。

---

## 5. 后续计划

- 为 `sage-kernel`, `sage-libs`, `sage-middleware` 编写覆盖率基准，确保 `codecov.yml` 的下限生效。
- 继续扩充 `pip-installation-test.yml` 中的导入矩阵（如 `sage-studio`, `sage-gateway`）。
- 考虑在 `sage-dev project test` 增加 `--min-coverage` 阈值参数，让 CI 在覆盖率下降时直接失败。
