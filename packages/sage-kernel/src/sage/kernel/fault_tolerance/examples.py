"""
Fault Tolerance Usage Examples

Layer: L3 (Kernel - Examples)
Dependencies: sage.libs (L3 - optional examples only)

展示应用用户如何使用容错（无感知）以及开发者如何扩展容错策略。

⚠️ IMPORTANT - 架构说明:
    本文件是**可选示例代码**，不是 kernel 的核心功能。
    示例中使用 sage.libs 的 Source/Sink 是为了演示完整的容错流程。

    运行这些示例需要安装 sage.libs:
        pip install sage-libs

    用户可以使用自己的 Source/Sink 实现，无需依赖 sage.libs。

Architecture Note:
    这些示例演示完整的使用场景，需要 sage.libs 提供 Source/Sink。
    如果 sage.libs 不可用，示例将无法运行，但不影响 kernel 的核心功能。
"""

# ============================================================================
# 应用用户示例 - 容错配置对用户是透明的
# ============================================================================


def example_1_user_checkpoint_strategy():
    """
    示例 1: 应用用户使用 Checkpoint 策略

    用户只需在 Environment 配置中声明，无需编写任何容错代码。

    Requirements:
        pip install sage-libs
    """
    from sage.kernel.api.local_environment import LocalEnvironment

    # 此示例需要 sage.libs
    try:
        from sage.libs.io.sink import TerminalSink
        from sage.libs.io.source import FileSource
    except ImportError as e:
        raise ImportError(
            "This example requires sage.libs. "
            "Install it with: pip install sage-libs\n"
            "Or use your own Source/Sink implementations."
        ) from e

    # 创建环境时声明使用 Checkpoint 容错策略
    env = LocalEnvironment(
        "qa_pipeline_with_checkpoint",
        config={
            "fault_tolerance": {
                "strategy": "checkpoint",
                "checkpoint_interval": 60.0,  # 每60秒保存一次
                "max_recovery_attempts": 3,  # 最多恢复3次
                "checkpoint_dir": ".my_checkpoints",
            },
            "source": {"file_path": "data/questions.txt"},
            "sink": {},
        },
    )

    # 正常定义 DAG - 完全不需要关心容错
    pipeline = (
        env.from_source(FileSource, env.config["source"])
        .map(lambda x: x.upper())  # 一些处理
        .sink(TerminalSink, env.config["sink"])
    )

    # 提交作业 - 容错由系统自动处理
    # 如果任务失败，系统会自动从最近的 checkpoint 恢复
    env.submit()

    print("✅ Pipeline submitted with checkpoint fault tolerance")


def example_2_user_restart_strategy():
    """
    示例 2: 应用用户使用 Restart 策略

    使用指数退避重启策略，用户同样无需编写容错代码。

    Requirements:
        pip install sage-libs
    """
    from sage.kernel.api.local_environment import LocalEnvironment

    try:
        from sage.libs.io.sink import TerminalSink
        from sage.libs.io.source import FileSource
    except ImportError as e:
        raise ImportError(
            "This example requires sage.libs. "
            "Install it with: pip install sage-libs"
        ) from e

    # 使用指数退避重启策略
    env = LocalEnvironment(
        "data_pipeline_with_restart",
        config={
            "fault_tolerance": {
                "strategy": "restart",
                "restart_strategy": "exponential",
                "initial_delay": 1.0,  # 首次重启等待1秒
                "max_delay": 60.0,  # 最多等待60秒
                "multiplier": 2.0,  # 每次延迟翻倍
                "max_attempts": 5,  # 最多重启5次
            },
            "source": {"file_path": "data/input.txt"},
            "sink": {},
        },
    )

    # 定义 DAG - 用户不关心容错
    pipeline = (
        env.from_source(FileSource, env.config["source"])
        .map(lambda x: x.strip())
        .sink(TerminalSink, env.config["sink"])
    )

    # 提交 - 失败时自动重启
    env.submit()

    print("✅ Pipeline submitted with exponential backoff restart")


def example_3_user_no_fault_tolerance():
    """
    示例 3: 用户不配置容错（使用默认行为）

    Requirements:
        pip install sage-libs
    """
    from sage.kernel.api.local_environment import LocalEnvironment

    try:
        from sage.libs.io.sink import TerminalSink
        from sage.libs.io.source import FileSource
    except ImportError as e:
        raise ImportError(
            "This example requires sage.libs. "
            "Install it with: pip install sage-libs"
        ) from e

    # 不配置 fault_tolerance，使用默认行为
    env = LocalEnvironment("simple_pipeline")

    # 正常定义和提交
    pipeline = (
        env.from_source(FileSource, {"file_path": "data.txt"})
        .map(lambda x: x.upper())
        .sink(TerminalSink, {})
    )

    env.submit()

    print("✅ Pipeline submitted with default fault tolerance")


def example_4_user_yaml_config():
    """
    示例 4: 从 YAML 配置文件读取容错配置

    这是最常见的用法 - 配置在外部文件中管理。

    Requirements:
        pip install sage-libs
    """
    from sage.common.utils.config.loader import load_config
    from sage.kernel.api.local_environment import LocalEnvironment

    try:
        from sage.libs.io.sink import TerminalSink
        from sage.libs.io.source import FileSource
    except ImportError as e:
        raise ImportError(
            "This example requires sage.libs. "
            "Install it with: pip install sage-libs"
        ) from e

    # config.yaml 内容示例：
    # fault_tolerance:
    #   strategy: checkpoint
    #   checkpoint_interval: 30.0
    #   max_recovery_attempts: 5
    # source:
    #   file_path: data/input.txt
    # sink: {}

    config = load_config("config/my_pipeline.yaml")

    # 容错配置从 YAML 文件读取
    env = LocalEnvironment("yaml_configured_pipeline", config=config)

    pipeline = (
        env.from_source(FileSource, config["source"])
        .map(lambda x: x.strip())
        .sink(TerminalSink, config["sink"])
    )

    env.submit()

    print("✅ Pipeline submitted with YAML-configured fault tolerance")


# ============================================================================
# 开发者示例 - 扩展自定义容错策略
# ============================================================================


def example_5_developer_custom_strategy():
    """
    示例 5: 开发者实现自定义容错策略

    开发者可以继承 BaseFaultHandler 实现自己的容错逻辑。
    """
    from sage.kernel.fault_tolerance.base import BaseFaultHandler

    class CircuitBreakerFaultHandler(BaseFaultHandler):
        """
        断路器容错策略

        当失败次数超过阈值时，打开断路器，停止重试一段时间。
        """

        def __init__(self, failure_threshold=5, timeout=60.0):
            self.failure_threshold = failure_threshold
            self.timeout = timeout
            self.failure_counts = {}
            self.circuit_open = {}
            self.open_time = {}
            self.logger = None

        def handle_failure(self, task_id: str, error: Exception) -> bool:
            import time

            # 更新失败计数
            if task_id not in self.failure_counts:
                self.failure_counts[task_id] = 0
            self.failure_counts[task_id] += 1

            if self.logger:
                self.logger.warning(
                    f"Task {task_id} failed (count: {self.failure_counts[task_id]}): {error}"
                )

            # 检查是否应该打开断路器
            if self.failure_counts[task_id] >= self.failure_threshold:
                self.circuit_open[task_id] = True
                self.open_time[task_id] = time.time()

                if self.logger:
                    self.logger.error(
                        f"Circuit breaker opened for {task_id} "
                        f"(failures: {self.failure_counts[task_id]})"
                    )
                return False

            return self.recover(task_id)

        def can_recover(self, task_id: str) -> bool:
            import time

            # 如果断路器是打开的
            if self.circuit_open.get(task_id, False):
                # 检查是否已经超过超时时间
                if time.time() - self.open_time.get(task_id, 0) > self.timeout:
                    # 关闭断路器，重置计数
                    self.circuit_open[task_id] = False
                    self.failure_counts[task_id] = 0

                    if self.logger:
                        self.logger.info(f"Circuit breaker closed for {task_id}")

                    return True
                return False

            return self.failure_counts.get(task_id, 0) < self.failure_threshold

        def recover(self, task_id: str) -> bool:
            if self.logger:
                self.logger.info(f"Attempting to recover task {task_id}")

            # 实际的恢复逻辑
            # TODO: 实现具体的恢复策略
            # Issue URL: https://github.com/intellistream/SAGE/issues/933

            return True

    print("✅ Custom CircuitBreakerFaultHandler defined")
    print("   Developers can extend BaseFaultHandler to create custom strategies")


def example_6_developer_register_strategy():
    """
    示例 6: 开发者将自定义策略集成到系统

    步骤：
    1. 将自定义策略类放到 impl/ 目录
    2. 在 impl/__init__.py 中导出
    3. 在 factory.py 中添加创建逻辑
    4. 用户就可以通过配置使用了
    """

    # 步骤 1: 创建自定义策略文件
    # packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/circuit_breaker.py

    # 步骤 2: 在 impl/__init__.py 添加导出
    # from sage.kernel.fault_tolerance.impl.circuit_breaker import CircuitBreakerFaultHandler
    # __all__ = [..., "CircuitBreakerFaultHandler"]

    # 步骤 3: 在 factory.py 添加创建逻辑
    # def create_fault_handler_from_config(config):
    #     strategy = config.get("strategy")
    #     if strategy == "circuit_breaker":
    #         return CircuitBreakerFaultHandler(
    #             failure_threshold=config.get("failure_threshold", 5),
    #             timeout=config.get("timeout", 60.0)
    #         )
    #     ...

    # 步骤 4: 用户现在可以通过配置使用
    # env = LocalEnvironment(
    #     "my_app",
    #     config={
    #         "fault_tolerance": {
    #             "strategy": "circuit_breaker",
    #             "failure_threshold": 3,
    #             "timeout": 30.0
    #         }
    #     }
    # )

    print("✅ Custom strategy integration steps:")
    print("   1. Create strategy class in impl/")
    print("   2. Export in impl/__init__.py")
    print("   3. Add creation logic in factory.py")
    print("   4. Users can now use it via config")


def example_7_developer_reference_implementations():
    """
    示例 7: 开发者参考现有实现

    查看 impl/ 目录下的实现来学习如何编写容错策略。
    """
    print("✅ Reference implementations in impl/:")
    print("   - checkpoint_recovery.py: Checkpoint-based fault tolerance")
    print("   - restart_recovery.py: Restart-based fault tolerance")
    print("   - restart_strategy.py: Various restart strategies")
    print("   - lifecycle_impl.py: Lifecycle management")
    print("   - checkpoint_impl.py: Checkpoint management")


# ============================================================================
# 运行所有示例
# ============================================================================


def run_user_examples():
    """运行应用用户示例"""
    print("\n" + "=" * 70)
    print("APPLICATION USER EXAMPLES - Fault Tolerance is Transparent")
    print("=" * 70 + "\n")

    print("Example 1: Checkpoint Strategy")
    print("-" * 70)
    example_1_user_checkpoint_strategy()

    print("\nExample 2: Restart Strategy with Exponential Backoff")
    print("-" * 70)
    example_2_user_restart_strategy()

    print("\nExample 3: No Explicit Fault Tolerance Configuration")
    print("-" * 70)
    example_3_user_no_fault_tolerance()

    print("\nExample 4: YAML Configuration")
    print("-" * 70)
    example_4_user_yaml_config()


def run_developer_examples():
    """运行开发者扩展示例"""
    print("\n" + "=" * 70)
    print("DEVELOPER EXAMPLES - Extending Fault Tolerance Strategies")
    print("=" * 70 + "\n")

    print("Example 5: Custom Circuit Breaker Strategy")
    print("-" * 70)
    example_5_developer_custom_strategy()

    print("\nExample 6: Integrating Custom Strategy into System")
    print("-" * 70)
    example_6_developer_register_strategy()

    print("\nExample 7: Reference Implementations")
    print("-" * 70)
    example_7_developer_reference_implementations()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "FAULT TOLERANCE EXAMPLES" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")

    run_user_examples()
    run_developer_examples()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70 + "\n")
