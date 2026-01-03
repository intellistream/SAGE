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


def get_algorithm_params_from_config(algo_name: str, dataset: str = "random-xs") -> dict[str, Any]:
    """
    从配置文件获取算法参数（用于生成结果文件夹名）

    Args:
        algo_name: 算法名称（可能包含后缀，如 vsag_hnsw_no_opt）
        dataset: 数据集名称

    Returns:
        包含构建参数和查询参数的字典
    """
    config_path = Path(__file__).parent / algo_name / "config.yaml"

    # 处理带后缀的算法名（如 vsag_hnsw_no_opt -> vsag_hnsw）
    base_algo_name = algo_name

    if not config_path.exists():
        # 尝试查找基础算法名的配置
        for i in range(len(algo_name.split("_")) - 1, 0, -1):
            test_base = "_".join(algo_name.split("_")[:i])
            test_path = Path(__file__).parent / test_base / "config.yaml"
            if test_path.exists():
                config_path = test_path
                base_algo_name = test_base
                break

    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # 查找数据集配置，优先使用完整算法名
        if dataset not in config:
            return {}

        dataset_config = config[dataset]
        algo_key = algo_name if algo_name in dataset_config else base_algo_name

        if algo_key not in dataset_config:
            return {}

        algo_config = dataset_config[algo_key]

        result = {
            "build_params": {},
            "query_params": {},
        }

        # 解析 run-groups 中的参数
        if "run-groups" in algo_config:
            run_groups = algo_config["run-groups"]
            if "base" in run_groups:
                base_group = run_groups["base"]

                # 解析 args（构建参数）
                if "args" in base_group:
                    args_str = base_group["args"]
                    if isinstance(args_str, str):
                        args_str = args_str.strip()
                        import ast

                        try:
                            args_list = ast.literal_eval(args_str)
                            if args_list and isinstance(args_list, list):
                                result["build_params"] = args_list[0]
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
                                result["query_params"] = query_args_list[0]
                        except Exception:
                            pass

        return result
    except Exception as e:
        print(f"⚠ Failed to get params for {algo_name}: {e}")

    return {}


def get_all_algorithm_param_combinations(
    algo_name: str, dataset: str = "random-xs"
) -> list[dict[str, Any]]:
    """
    获取算法配置中所有参数组合（args × query-args 的笛卡尔积）

    Args:
        algo_name: 算法名称（支持带后缀，如 vsag_hnsw_no_opt -> vsag_hnsw）
        dataset: 数据集名称

    Returns:
        参数组合列表，每个元素包含 build_params 和 query_params
    """
    import ast
    import itertools

    config_path = Path(__file__).parent / algo_name / "config.yaml"
    base_algo_name = algo_name

    # 处理带后缀的算法名
    if not config_path.exists():
        parts = algo_name.split("_")
        for i in range(len(parts) - 1, 0, -1):
            test_base = "_".join(parts[:i])
            test_path = Path(__file__).parent / test_base / "config.yaml"
            if test_path.exists():
                config_path = test_path
                base_algo_name = test_base
                break

    if not config_path.exists():
        return [{"build_params": {}, "query_params": {}}]

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        if dataset not in config:
            return [{"build_params": {}, "query_params": {}}]

        dataset_config = config[dataset]
        algo_key = algo_name if algo_name in dataset_config else base_algo_name

        if algo_key not in dataset_config:
            return [{"build_params": {}, "query_params": {}}]

        algo_config = dataset_config[algo_key]

        build_params_list = [{}]
        query_params_list = [{}]

        # 解析 run-groups 中的参数
        if "run-groups" in algo_config:
            run_groups = algo_config["run-groups"]
            if "base" in run_groups:
                base_group = run_groups["base"]

                # 解析 args（构建参数列表）
                if "args" in base_group:
                    args_str = base_group["args"]
                    if isinstance(args_str, str):
                        args_str = args_str.strip()
                        try:
                            args_list = ast.literal_eval(args_str)
                            if args_list and isinstance(args_list, list):
                                build_params_list = args_list
                        except Exception:
                            pass

                # 解析 query-args（查询参数列表）
                if "query-args" in base_group:
                    query_args_str = base_group["query-args"]
                    if isinstance(query_args_str, str):
                        query_args_str = query_args_str.strip()
                        try:
                            query_args_list = ast.literal_eval(query_args_str)
                            if query_args_list and isinstance(query_args_list, list):
                                query_params_list = query_args_list
                        except Exception:
                            pass

        # 生成笛卡尔积
        combinations = []
        for build_params, query_params in itertools.product(build_params_list, query_params_list):
            combinations.append({"build_params": build_params, "query_params": query_params})

        return combinations if combinations else [{"build_params": {}, "query_params": {}}]

    except Exception as e:
        print(f"⚠ Failed to get param combinations for {algo_name}: {e}")
        return [{"build_params": {}, "query_params": {}}]


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

    # 处理带后缀的算法名（如 vsag_hnsw_no_opt -> vsag_hnsw）
    base_algo_name = algo_name

    if not config_path.exists():
        # 尝试查找基础算法名的配置
        parts = algo_name.rsplit("_", 1)
        if len(parts) == 2:
            # 尝试多种分割方式
            for i in range(len(algo_name.split("_")) - 1, 0, -1):
                test_base = "_".join(algo_name.split("_")[:i])
                test_path = Path(__file__).parent / test_base / "config.yaml"
                if test_path.exists():
                    config_path = test_path
                    base_algo_name = test_base
                    break

    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # 查找数据集配置，支持带后缀的算法名
        algo_key = algo_name if algo_name in config.get(dataset, {}) else base_algo_name

        if dataset in config and algo_key in config[dataset]:
            algo_config = config[dataset][algo_key]

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
        CANDYWrapper,
        get_candy_algorithm,
    )

    print("✓ Legacy CANDY wrapper still available")
    _ = (CANDYWrapper, get_candy_algorithm)
except ImportError:
    pass


# 尝试导入 Faiss 算法包装器（向后兼容）
try:
    from .faiss_wrapper import FaissWrapper

    print("✓ Legacy Faiss wrapper still available")
    _ = FaissWrapper
except ImportError:
    pass


# 尝试导入 DiskANN 算法包装器（向后兼容）
try:
    from .diskann_wrapper import DiskANNWrapper

    print("✓ Legacy DiskANN wrapper still available")
    _ = DiskANNWrapper
except ImportError:
    pass
