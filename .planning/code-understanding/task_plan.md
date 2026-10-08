# PipelineCompiler 缓存接入与相邻重构
- [complete] 确认结构计划/运行状态边界与现有执行缺陷。
- [complete] 接入共享有界缓存，隔离每次绑定的输入、函数、actor 和服务状态。
- [complete] 修复相邻图路由/生命周期问题，加入针对性回归测试。
- [complete] 验证并更新开发文档与变更记录。

授权：用户要求实际接入并重构不合理实现；限相关编译/执行/缓存边界，不操作外部服务或硬件。

## 验证
- 完整 src/tests：190 passed, 1 skipped, 7 deprecation warnings，5.15 秒。
- Python：/home/shuhao/miniconda3/bin/python 3.13；禁用宿主无关 pytest 插件自动加载。
- Ruff lint、format 检查通过；release/tools 边界 PASS；git diff --check 通过。
- 尚无端到端性能收益或跨机器执行的验证结论；缓存仅复用结构计划。

## 遇到的问题与处理
- 系统 python3 缺少 cloudpickle：改用已有依赖完整的 Conda base Python，没有安装新依赖。
- 基线 24 项测试中 1 项 round-robin 失败：确认副本选择受线程调度影响，修复并补确定性反序执行测试。
- 个别路径搜索把包当成模块文件：按实际文件布局修正，无代码影响。
