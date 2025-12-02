"""
Algorithm Registry

自动发现并注册算法实现（从各个算法目录中加载）
"""

import importlib
from pathlib import Path
from typing import Any, Callable

import yaml

from .base import BaseANN, DummyStreamingANN

# 算法注册表
ALGORITHMS: dict[str, Callable[..., BaseANN]] = {
    "dummy": lambda: DummyStreamingANN(),
}


def register_algorithm(name: str, factory: Callable[..., BaseANN]) -> None:
    """
    注册新算法

    Args:
        name: 算法名称
        factory: 返回算法实例的工厂函数
    """
    ALGORITHMS[name] = factory


def get_algorithm(name: str, dataset: str = "random-xs", **kwargs) -> BaseANN:
    """
    根据名称获取算法实例

    Args:
        name: 算法名称
        dataset: 数据集名称（用于选择配置）
        **kwargs: 传递给算法构造函数的参数（会覆盖配置文件中的默认值）

    Returns:
        算法实例
    """
    if name not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {name}. Available: {list(ALGORITHMS.keys())}")

    # 尝试从配置文件读取默认参数
    default_params = _load_algorithm_config(name, dataset)

    # 合并参数：命令行参数优先
    merged_params = {**default_params, **kwargs}

    factory = ALGORITHMS[name]
    return factory(**merged_params) if merged_params else factory()


def _load_algorithm_config(algo_name: str, dataset: str = "random-xs") -> dict[str, Any]:
    """
    从配置文件加载算法默认参数

    Args:
        algo_name: 算法名称
        dataset: 数据集名称

    Returns:
        参数字典
    """
    config_path = Path(__file__).parent / algo_name / "config.yaml"

    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # 查找数据集配置
        if dataset in config and algo_name in config[dataset]:
            algo_config = config[dataset][algo_name]

            # 提取基础参数
            params = {}

            # 解析 base-args（通常包含 metric）
            if "base-args" in algo_config:
                base_args = algo_config["base-args"]
                # 处理 @metric 占位符
                if base_args and isinstance(base_args, list):
                    if "@metric" in base_args:
                        params["metric"] = "euclidean"  # 默认距离度量

            # 解析 run-groups 中的参数
            if "run-groups" in algo_config:
                run_groups = algo_config["run-groups"]
                if "base" in run_groups:
                    base_group = run_groups["base"]

                    # 解析 args（索引参数）
                    if "args" in base_group:
                        args_str = base_group["args"]
                        if isinstance(args_str, str):
                            # 去除 YAML 中的多行字符串标记
                            args_str = args_str.strip()
                            # 解析为 Python 字面量
                            import ast

                            try:
                                args_list = ast.literal_eval(args_str)
                                if args_list and isinstance(args_list, list):
                                    params["index_params"] = args_list[0]
                            except Exception:
                                pass

                    # 解析 query-args（查询参数）
                    if "query-args" in base_group:
                        query_args_str = base_group["query-args"]
                        if isinstance(query_args_str, str):
                            query_args_str = query_args_str.strip()
                            import ast

                            try:
                                query_args_list = ast.literal_eval(query_args_str)
                                if query_args_list and isinstance(query_args_list, list):
                                    # 使用第一个查询参数作为默认值
                                    if params.get("index_params"):
                                        params["index_params"].update(query_args_list[0])
                                    else:
                                        params["index_params"] = query_args_list[0]
                            except Exception:
                                pass

            return params
    except Exception as e:
        print(f"⚠ Failed to load config for {algo_name}: {e}")

    return {}


def discover_algorithms() -> list[str]:
    """
    自动发现所有算法文件夹

    Returns:
        算法名称列表
    """
    current_dir = Path(__file__).parent
    algorithm_dirs = []

    for item in current_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_") and not item.name.startswith("."):
            # 检查是否包含 Python 文件
            py_file = item / f"{item.name}.py"
            if py_file.exists():
                algorithm_dirs.append(item.name)

    return algorithm_dirs


def auto_register_algorithms():
    """
    自动注册所有发现的算法
    """
    algorithms = discover_algorithms()

    for algo_name in algorithms:
        try:
            # 使用相对导入（benchmark_anns是独立项目）
            module_path = f".{algo_name}.{algo_name}"
            module = importlib.import_module(module_path, package="bench.algorithms")

            # 尝试多种类名格式
            possible_class_names = [
                # 原始带下划线的类名
                algo_name.replace("_", "_").title().replace("_", "_"),  # Faiss_HNSW
                "".join(word.capitalize() for word in algo_name.split("_")),  # FaissHNSW
                algo_name.upper(),  # FAISS_HNSW
                algo_name.capitalize(),  # Faiss_hnsw
            ]

            # 尝试找到类
            algo_class = None
            for class_name in possible_class_names:
                if hasattr(module, class_name):
                    algo_class = getattr(module, class_name)
                    break

            # 如果找不到，尝试获取模块中所有的 BaseStreamingANN 子类
            if algo_class is None:
                import inspect

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if name != "BaseStreamingANN" and hasattr(obj, "__bases__"):
                        # 检查是否继承自 BaseStreamingANN
                        try:
                            if "BaseStreamingANN" in [base.__name__ for base in obj.__bases__]:
                                algo_class = obj
                                break
                        except Exception:
                            pass

            if algo_class:
                # 注册为工厂函数 - 返回实例化的对象
                def make_factory(cls):
                    return lambda **kwargs: cls(**kwargs)

                ALGORITHMS[algo_name] = make_factory(algo_class)
                print(f"✓ Registered algorithm: {algo_name}")
            else:
                print(f"⚠ Algorithm class not found in {module_path}")
        except Exception as e:
            print(f"⚠ Failed to register {algo_name}: {e}")


# 自动注册所有算法
auto_register_algorithms()


# 保留旧的兼容性导入（已弃用）
# 尝试导入 CANDY 算法包装器（向后兼容）
try:
    from .candy_wrapper import (
        CANDYWrapper,  # noqa: F401
        get_candy_algorithm,  # noqa: F401
    )

    print("✓ Legacy CANDY wrapper still available")
except ImportError:
    pass


# 尝试导入 Faiss 算法包装器（向后兼容）
try:
    from .faiss_wrapper import FaissWrapper  # noqa: F401

    print("✓ Legacy Faiss wrapper still available")
except ImportError:
    pass


# 尝试导入 DiskANN 算法包装器（向后兼容）
try:
    from .diskann_wrapper import DiskANNWrapper  # noqa: F401

    print("✓ Legacy DiskANN wrapper still available")
except ImportError:
    pass
