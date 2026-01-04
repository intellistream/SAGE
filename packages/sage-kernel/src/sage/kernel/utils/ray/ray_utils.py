from pathlib import Path

try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    ray = None  # type: ignore[assignment]
    RAY_AVAILABLE = False

try:
    from sage.common.config.output_paths import get_sage_paths

    SAGE_OUTPUT_PATHS_AVAILABLE = True
except ImportError:
    SAGE_OUTPUT_PATHS_AVAILABLE = False


def normalize_extra_python_paths(paths) -> list[str]:
    """Normalize extra python paths to a string list."""
    if paths is None:
        return []
    if isinstance(paths, str):
        return [paths]
    try:
        iterable = list(paths)
    except TypeError:
        return [str(paths)]

    normalized: list[str] = []
    for item in iterable:
        if item is None:
            continue
        normalized.append(str(item))
    return normalized


def get_sage_kernel_runtime_env():
    """
    获取Sage内核的Ray运行环境配置，确保Actor可以访问sage模块
    """
    import os

    # 动态获取sage-kernel源码路径
    current_file = os.path.abspath(__file__)
    # 从当前文件往上找到sage-kernel/src目录
    parts = current_file.split("/")
    try:
        kernel_idx = next(i for i, part in enumerate(parts) if part == "sage-kernel")
        sage_kernel_src = "/".join(parts[: kernel_idx + 1]) + "/src"
    except StopIteration:
        # 备用方法：从环境变量或当前工作目录推断
        cwd = os.getcwd()
        if "sage-kernel" in cwd:
            parts = cwd.split("/")
            kernel_idx = next(i for i, part in enumerate(parts) if part == "sage-kernel")
            sage_kernel_src = "/".join(parts[: kernel_idx + 1]) + "/src"
        else:
            # 最后的备用方法
            sage_kernel_src = os.path.expanduser("~/SAGE/packages/sage-kernel/src")

    if not os.path.exists(sage_kernel_src):
        print(f"警告：无法找到sage-kernel源码路径: {sage_kernel_src}")
        return {}

    # 构建runtime_env配置
    # 添加 experiments 目录以支持分布式调度实验
    pythonpath_parts = [sage_kernel_src]
    experiments_dir = os.path.abspath(
        os.path.join(os.path.dirname(sage_kernel_src), "../../../experiments")
    )
    if os.path.exists(experiments_dir):
        pythonpath_parts.append(experiments_dir)

    pythonpath = ":".join(pythonpath_parts)
    if os.environ.get("PYTHONPATH"):
        pythonpath += ":" + os.environ.get("PYTHONPATH")

    runtime_env = {
        "py_modules": [sage_kernel_src],
        "env_vars": {"PYTHONPATH": pythonpath},
    }

    return runtime_env


def _prepare_ray_temp_dir() -> Path | None:
    """Resolve the Ray temp directory, preferring SAGE-managed paths."""
    import os

    ray_temp_dir = None

    if SAGE_OUTPUT_PATHS_AVAILABLE:
        try:
            sage_paths = get_sage_paths()  # type: ignore[possibly-unbound]
            sage_paths.setup_environment_variables()
            ray_temp_dir = sage_paths.get_ray_temp_dir()
        except Exception as e:  # pragma: no cover - defensive path
            print(f"Warning: Failed to set Ray temp directory via output_paths: {e}")

    if ray_temp_dir is None:
        try:
            fallback = Path.home() / ".sage" / "temp" / "ray"
            fallback.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("SAGE_TEMP_DIR", str(fallback.parent))
            os.environ.setdefault("RAY_TMPDIR", str(fallback))
            ray_temp_dir = fallback
            print(f"Ray will use fallback temp directory: {fallback}")
        except Exception as e:  # pragma: no cover - defensive path
            print(f"Warning: Failed to prepare fallback Ray temp directory: {e}")
            return None

    return ray_temp_dir


def init_ray_with_sage_temp(**init_kwargs):
    """Initialize Ray with SAGE temp directory defaults."""
    if not RAY_AVAILABLE:
        raise ImportError("Ray is not available")

    ray_temp_dir = _prepare_ray_temp_dir()
    if ray_temp_dir is not None:
        init_kwargs.setdefault("_temp_dir", str(ray_temp_dir))

    return ray.init(**init_kwargs)  # type: ignore[union-attr]


def ensure_ray_initialized(runtime_env=None):
    """
    确保Ray已经初始化，如果没有则初始化Ray。

    优先尝试连接到现有的 Ray 集群（address="auto"），
    如果没有集群则启动本地 Ray 实例。

    Args:
        runtime_env: Ray运行环境配置，如果为None则使用默认的sage配置
    """
    if not RAY_AVAILABLE:
        raise ImportError("Ray is not available")

    # ray 在 RAY_AVAILABLE=True 时总是有效的
    if not ray.is_initialized():  # type: ignore[union-attr]
        try:
            import os

            # 检测是否在CI环境中
            is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"

            # 准备初始化参数（本地模式）
            init_kwargs = {
                "ignore_reinit_error": True,
                "num_cpus": 2 if is_ci else 16,  # CI环境使用更少的CPU
                "num_gpus": 0,  # 不使用GPU
                "object_store_memory": 100000000 if is_ci else 200000000,  # CI: 100MB, 本地: 200MB
                "log_to_driver": False,  # 减少日志输出
                "include_dashboard": False,  # 禁用dashboard减少资源占用
            }

            # 如果提供了runtime_env，使用它；否则使用默认的sage配置
            if runtime_env is not None:
                init_kwargs["runtime_env"] = runtime_env
            else:
                # 使用默认的sage配置
                sage_runtime_env = get_sage_kernel_runtime_env()
                if sage_runtime_env:
                    init_kwargs["runtime_env"] = sage_runtime_env

            # 使用标准模式但限制资源，支持async actors和队列
            init_ray_with_sage_temp(**init_kwargs)
            mode = "CI mode" if is_ci else "standard mode"
            print(f"Ray initialized in {mode} with limited resources")
        except Exception as e:
            print(f"Failed to initialize Ray: {e}")
            raise
    else:
        # Ray 已经初始化，检查节点数量
        try:
            nodes = ray.nodes()
            alive_nodes = [n for n in nodes if n.get("Alive", False)]
            print(f"Ray is already initialized with {len(alive_nodes)} nodes")
        except Exception:
            print("Ray is already initialized.")


def is_distributed_environment() -> bool:
    """
    检查是否在分布式环境中运行。
    尝试导入Ray并检查是否已初始化。
    """
    if not RAY_AVAILABLE:
        return False

    try:
        # ray 在 RAY_AVAILABLE=True 时总是有效的
        return ray.is_initialized()  # type: ignore[union-attr]
    except Exception:
        return False
