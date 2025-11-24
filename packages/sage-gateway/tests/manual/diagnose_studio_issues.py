#!/usr/bin/env python3
"""
Studio 问题诊断脚本

诊断3个问题:
1. chat生成的工作流导入进studio是空壳
2. 新建聊天时好时坏
3. studio playground输入问题回答报错
"""

import json
import sys
from pathlib import Path


def test_session_creation():
    """测试 Session 创建（问题2）"""
    print("\n" + "=" * 70)
    print("问题2: 测试 Session 创建")
    print("=" * 70)

    try:
        from sage.gateway.session.manager import SessionManager

        manager = SessionManager()

        # Test multiple session creation
        for i in range(5):
            session = manager.get_or_create(None)
            print(f"  [{i + 1}] Session created: {session.id[:8]}... - Title: {session.title}")

        print("✅ Session 创建正常 - 问题可能在前端或 API 层")
        return True

    except Exception as e:
        print(f"❌ Session 创建失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_playground_execution():
    """测试 Playground 执行（问题3）"""
    print("\n" + "=" * 70)
    print("问题3: 测试 Playground 执行")
    print("=" * 70)

    try:
        from sage.studio.services.playground_executor import (
            PlaygroundExecutor,
            PlaygroundSource,
            PlaygroundSink,
        )
        from sage.kernel.api import LocalEnvironment

        # Simple test flow

        PlaygroundExecutor()
        print("  ✓ PlaygroundExecutor 创建成功")

        # Test simple execution
        env = LocalEnvironment()
        source = PlaygroundSource(question="测试问题")
        sink = PlaygroundSink(execution_id="test-exec")

        env.from_source(source).add_sink(sink)
        job = env.submit(autostop=True)

        import time

        timeout = 5
        start = time.time()
        while job.is_running() and (time.time() - start) < timeout:
            time.sleep(0.1)

        results = PlaygroundSink.get_results("test-exec")
        print(f"  ✓ 执行完成，结果数: {len(results)}")
        print(f"    结果: {results}")

        if results:
            print("✅ Playground 基础执行正常")
            return True
        else:
            print("⚠️  Playground 执行成功但无结果 - 可能需要检查具体节点")
            return True

    except Exception as e:
        print(f"❌ Playground 执行失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_workflow_export():
    """测试工作流导出（问题1）"""
    print("\n" + "=" * 70)
    print("问题1: 测试工作流导出/导入")
    print("=" * 70)

    # 检查 sage chat 是否生成工作流文件
    chat_dir = Path.home() / ".sage" / "chat"

    print(f"  检查目录: {chat_dir}")
    if chat_dir.exists():
        workflow_files = list(chat_dir.glob("*.json"))
        print(f"  ✓ 找到 {len(workflow_files)} 个 JSON 文件")

        for wf_file in workflow_files[:3]:  # 只看前3个
            print(f"\n  📄 文件: {wf_file.name}")
            try:
                with open(wf_file) as f:
                    wf_data = json.load(f)
                    print(f"    - 键: {list(wf_data.keys())}")

                    if "nodes" in wf_data:
                        print(f"    - 节点数: {len(wf_data['nodes'])}")
                        if wf_data["nodes"]:
                            print(f"    - 第一个节点: {wf_data['nodes'][0]}")
                    else:
                        print("    ⚠️  缺少 'nodes' 字段")

                    if "edges" in wf_data:
                        print(f"    - 边数: {len(wf_data['edges'])}")
                    else:
                        print("    ⚠️  缺少 'edges' 字段")

            except Exception as e:
                print(f"    ❌ 解析失败: {e}")
    else:
        print(f"  ⚠️  目录不存在: {chat_dir}")

    # 检查 Studio 导入逻辑
    print("\n  检查 Studio 工作流导入逻辑...")
    try:
        from sage.studio.services.pipeline_builder import PipelineBuilder

        PipelineBuilder()
        print("  ✓ PipelineBuilder 可用")

        # TODO: 测试实际导入流程
        print("  ⚠️  需要检查 Studio 前端的导入逻辑")

    except Exception as e:
        print(f"  ❌ PipelineBuilder 导入失败: {e}")

    return True


def main():
    """运行所有诊断"""
    print("=" * 70)
    print("SAGE Studio 问题诊断")
    print("=" * 70)

    results = {
        "workflow_export": test_workflow_export(),
        "session_creation": test_session_creation(),
        "playground_execution": test_playground_execution(),
    }

    print("\n" + "=" * 70)
    print("诊断总结")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")

    print("\n下一步:")
    print("  1. 检查 Gateway 日志: ~/.sage/studio/chat/gateway.log")
    print("  2. 检查 Playground 日志: ~/.sage/logs/")
    print("  3. 运行 Studio 并查看浏览器控制台")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
