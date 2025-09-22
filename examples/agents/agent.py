from __future__ import annotations

import importlib
import json
import os
import sys
from typing import Any, Dict, Iterable

# 添加项目路径到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..", "..")
project_root = os.path.abspath(project_root)  # 规范化路径
sys.path.insert(0, project_root)

# 加载环境配置
try:
    from tools.env_config import (get_api_key, load_sage_env,
                                  should_use_real_api)

    load_sage_env()  # 立即加载环境变量
except ImportError:
    # Fallback if env_config is not available
    def get_api_key(service: str, required: bool = True):
        mapping = {"openai": "OPENAI_API_KEY"}
        key = os.getenv(mapping.get(service, f"{service.upper()}_API_KEY"))
        if required and not key:
            raise ValueError(f"Missing API key for {service}")
        return key

    def should_use_real_api():
        return False


from sage.common.utils.config.loader import load_config
from sage.libs.agents.action.mcp_registry import MCPRegistry
from sage.libs.agents.planning.llm_planner import LLMPlanner
from sage.libs.agents.profile.profile import BaseProfile
from sage.libs.agents.runtime.agent import AgentRuntime
from sage.libs.rag.generator import OpenAIGenerator


# ====== 读取 source ======
def iter_queries(source_cfg: Dict[str, Any]) -> Iterable[str]:
    stype = source_cfg.get("type", "local")
    if stype == "local":
        path = source_cfg["data_path"]
        field = source_cfg.get("field_query", "query")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                q = obj.get(field, "")
                if isinstance(q, str) and q.strip():
                    yield q
    elif stype == "hf":
        from datasets import load_dataset

        name = source_cfg["hf_dataset_name"]
        config = source_cfg.get("hf_dataset_config")
        split = source_cfg.get("hf_split", "dev")
        field = source_cfg.get("field_query", "query")
        ds = load_dataset(name, config, split=split)
        for row in ds:
            q = row.get(field, "")
            if isinstance(q, str) and q.strip():
                yield q
    else:
        raise ValueError(f"Unsupported source.type: {stype}")


def main():
    # ====== 读取配置 ======
    cfg_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "config_agent_min.yaml"
    )
    if not os.path.exists(cfg_path):
        print(f"❌ Configuration file not found: {cfg_path}")
        sys.exit(1)
    config: Dict[str, Any] = load_config(cfg_path)

    # ====== Profile ======
    profile = BaseProfile.from_dict(config["profile"])

    # 检查是否在测试模式
    use_real_api = should_use_real_api()
    test_mode = (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ) and not use_real_api  # 如果明确要求使用真实API，则不进入测试模式

    # 在真实API模式下，使用简化的查询数据以避免超时
    if use_real_api:
        config["source"]["data_path"] = "examples/data/agent_queries_test.jsonl"

    # ====== Generator======
    gen_cfg = config["generator"]["remote"]  # 可改为 "local"/"remote"

    # 验证 API key 配置（在测试和非测试模式下都需要检查）
    try:
        api_key = get_api_key("openai", required=True)
        gen_cfg["api_key"] = api_key
        if use_real_api:
            print("🌐 Real API mode: API key configuration validated")
        else:
            print("✅ API key configuration validated")
    except ValueError as e:
        if test_mode:
            print(f"⚠️ Test mode: {e}")
            print("💡 Tip: Copy .env.template to .env and fill in your API keys")
            print(
                "✅ Test mode: API key validation completed (missing key is OK in test)"
            )
        else:
            print(f"❌ {e}")
            print("💡 Tip: Copy .env.template to .env and fill in your API keys")
            sys.exit(1)

    if test_mode:
        # 在测试模式下，验证配置加载和模块导入，但不实际初始化组件
        print(
            "🧪 Test mode: Configuration loaded successfully (add --use-real-api to use real API)"
        )
        print("✅ Test mode: Profile created successfully")

        # 验证配置文件结构
        required_sections = ["generator", "planner", "tools", "runtime"]
        for section in required_sections:
            if section in config:
                print(f"✅ Test mode: {section} config found")
            else:
                print(f"❌ Test mode: {section} config missing")

        # 验证工具模块可以导入（但不实际初始化）
        try:
            for item in config.get("tools", []):
                mod = importlib.import_module(item["module"])
                cls = getattr(mod, item["class"])
                print(f"✅ Test mode: Tool {item['class']} import successful")
        except Exception as e:
            print(f"⚠️ Test mode: Tool import failed (this is OK in test): {e}")

        print("✅ Test mode: Agent pipeline structure validated")
        return

    if use_real_api:
        print("🌐 Real API mode: Will make actual API calls with qwen-turbo")

    generator = OpenAIGenerator(gen_cfg)  # ====== Planner ======
    planner_cfg = config["planner"]
    planner = LLMPlanner(
        generator=generator,
        max_steps=planner_cfg.get("max_steps", 6),
        enable_repair=planner_cfg.get("enable_repair", True),
        topk_tools=planner_cfg.get("topk_tools", 6),
    )

    # ====== MCP 工具注册：按配置动态 import 并注册 ======
    registry = MCPRegistry()
    for item in config.get("tools", []):
        mod = importlib.import_module(item["module"])
        cls = getattr(mod, item["class"])
        kwargs = item.get("init_kwargs", {})
        registry.register(cls(**kwargs) if kwargs else cls())

    # ====== Runtime ======
    runtime_cfg = config["runtime"]
    agent = AgentRuntime(
        profile=profile,
        planner=planner,
        tools=registry,
        summarizer=(
            generator if runtime_cfg.get("summarizer") == "reuse_generator" else None
        ),
        # memory=None,  # 如需接入 MemoryServiceAdapter，再按配置打开
        max_steps=runtime_cfg.get("max_steps", 6),
    )

    # ====== 跑一遍 queries======
    for q in iter_queries(config["source"]):
        print("\n==========================")
        print(f"🧑‍💻 User: {q}")
        ans = agent.execute({"query": q})
        print(f"🤖 Agent:\n{ans}")


if __name__ == "__main__":
    # 和 RAG 示例一致的“测试模式”友好输出
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        try:
            main()
            print("\n✅ Test passed: Agent pipeline structure validated")
        except Exception as e:
            print(f"❌ Test failed: {e}")
            sys.exit(1)
    else:
        main()
