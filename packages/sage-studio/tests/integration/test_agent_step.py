"""
Tests for AgentStep Schema

验证 Multi-Agent 系统的 AgentStep 数据模型。
"""

from sage.studio.models.agent_step import (
    AgentStep,
    StepStatus,
    StepType,
    reasoning_step,
    response_step,
    tool_call_step,
    tool_result_step,
)


class TestStepType:
    """测试 StepType 枚举"""

    def test_all_step_types_defined(self):
        """验证所有步骤类型已定义"""
        assert StepType.REASONING.value == "reasoning"
        assert StepType.TOOL_CALL.value == "tool_call"
        assert StepType.TOOL_RESULT.value == "tool_result"
        assert StepType.RESPONSE.value == "response"

    def test_step_type_is_string_enum(self):
        """验证 StepType 是字符串枚举"""
        assert isinstance(StepType.REASONING, str)
        assert StepType.REASONING == "reasoning"

    def test_step_type_from_string(self):
        """测试从字符串创建 StepType"""
        assert StepType("reasoning") == StepType.REASONING
        assert StepType("tool_call") == StepType.TOOL_CALL


class TestStepStatus:
    """测试 StepStatus 枚举"""

    def test_all_statuses_defined(self):
        """验证所有状态已定义"""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"

    def test_status_is_string_enum(self):
        """验证 StepStatus 是字符串枚举"""
        assert isinstance(StepStatus.COMPLETED, str)
        assert StepStatus.COMPLETED == "completed"


class TestAgentStep:
    """测试 AgentStep dataclass"""

    def test_create_with_enum(self):
        """测试使用枚举创建 AgentStep"""
        step = AgentStep.create(
            type=StepType.REASONING,
            content="分析用户意图...",
        )

        assert step.type == StepType.REASONING
        assert step.content == "分析用户意图..."
        assert step.status == StepStatus.COMPLETED  # 默认值
        assert step.step_id is not None
        assert len(step.step_id) == 8

    def test_create_with_string(self):
        """测试使用字符串创建 AgentStep"""
        step = AgentStep.create(
            type="reasoning",
            content="分析中...",
            status="running",
        )

        assert step.type == StepType.REASONING
        assert step.status == StepStatus.RUNNING

    def test_create_with_metadata(self):
        """测试创建带元数据的 AgentStep"""
        step = AgentStep.create(
            type=StepType.TOOL_CALL,
            content="调用搜索工具",
            tool_name="knowledge_search",
            query="什么是 SAGE",
        )

        assert step.metadata["tool_name"] == "knowledge_search"
        assert step.metadata["query"] == "什么是 SAGE"

    def test_to_dict(self):
        """测试转换为字典"""
        step = AgentStep(
            step_id="abc12345",
            type=StepType.REASONING,
            content="思考中...",
            status=StepStatus.COMPLETED,
            metadata={"key": "value"},
        )

        data = step.to_dict()

        assert data["step_id"] == "abc12345"
        assert data["type"] == "reasoning"  # 字符串值
        assert data["content"] == "思考中..."
        assert data["status"] == "completed"  # 字符串值
        assert data["metadata"] == {"key": "value"}

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "step_id": "xyz78901",
            "type": "tool_call",
            "content": "搜索知识库",
            "status": "running",
            "metadata": {"tool_name": "search"},
        }

        step = AgentStep.from_dict(data)

        assert step.step_id == "xyz78901"
        assert step.type == StepType.TOOL_CALL
        assert step.content == "搜索知识库"
        assert step.status == StepStatus.RUNNING
        assert step.metadata["tool_name"] == "search"

    def test_from_dict_without_metadata(self):
        """测试从不含 metadata 的字典创建"""
        data = {
            "step_id": "test123",
            "type": "response",
            "content": "最终回答",
            "status": "completed",
        }

        step = AgentStep.from_dict(data)

        assert step.metadata == {}

    def test_roundtrip_serialization(self):
        """测试序列化往返"""
        original = AgentStep.create(
            type=StepType.TOOL_RESULT,
            content="找到 5 条记录",
            tool_name="search",
            count=5,
        )

        # 序列化再反序列化
        data = original.to_dict()
        restored = AgentStep.from_dict(data)

        assert restored.step_id == original.step_id
        assert restored.type == original.type
        assert restored.content == original.content
        assert restored.status == original.status
        assert restored.metadata == original.metadata

    def test_with_status(self):
        """测试更新状态方法"""
        step = AgentStep.create(
            type=StepType.TOOL_CALL,
            content="执行中...",
            status=StepStatus.RUNNING,
        )

        completed_step = step.with_status(StepStatus.COMPLETED)

        # 原实例不变
        assert step.status == StepStatus.RUNNING
        # 新实例更新
        assert completed_step.status == StepStatus.COMPLETED
        assert completed_step.step_id == step.step_id
        assert completed_step.content == step.content

    def test_with_status_string(self):
        """测试使用字符串更新状态"""
        step = AgentStep.create(StepType.REASONING, "分析中...")

        failed_step = step.with_status("failed")

        assert failed_step.status == StepStatus.FAILED


class TestFactoryFunctions:
    """测试便捷工厂函数"""

    def test_reasoning_step(self):
        """测试创建推理步骤"""
        step = reasoning_step("分析用户意图...")

        assert step.type == StepType.REASONING
        assert step.content == "分析用户意图..."
        assert step.status == StepStatus.COMPLETED

    def test_reasoning_step_with_metadata(self):
        """测试创建带元数据的推理步骤"""
        step = reasoning_step("分析中...", phase="intent_detection")

        assert step.metadata["phase"] == "intent_detection"

    def test_tool_call_step(self):
        """测试创建工具调用步骤"""
        step = tool_call_step("搜索知识库...", "knowledge_search")

        assert step.type == StepType.TOOL_CALL
        assert step.status == StepStatus.RUNNING  # 工具调用默认 RUNNING
        assert step.metadata["tool_name"] == "knowledge_search"

    def test_tool_call_step_with_params(self):
        """测试创建带参数的工具调用步骤"""
        step = tool_call_step(
            "搜索 SAGE 文档",
            "knowledge_search",
            query="SAGE 是什么",
            top_k=5,
        )

        assert step.metadata["tool_name"] == "knowledge_search"
        assert step.metadata["query"] == "SAGE 是什么"
        assert step.metadata["top_k"] == 5

    def test_tool_result_step(self):
        """测试创建工具结果步骤"""
        step = tool_result_step("找到 3 条相关记录", "knowledge_search")

        assert step.type == StepType.TOOL_RESULT
        assert step.status == StepStatus.COMPLETED
        assert step.metadata["tool_name"] == "knowledge_search"

    def test_tool_result_step_with_metadata(self):
        """测试创建带结果元数据的工具结果步骤"""
        step = tool_result_step(
            "搜索完成",
            "arxiv_search",
            result_count=10,
            elapsed_time=1.23,
        )

        assert step.metadata["result_count"] == 10
        assert step.metadata["elapsed_time"] == 1.23

    def test_response_step(self):
        """测试创建响应步骤"""
        step = response_step("SAGE 是一个 AI 框架...")

        assert step.type == StepType.RESPONSE
        assert step.content == "SAGE 是一个 AI 框架..."
        assert step.status == StepStatus.COMPLETED

    def test_response_step_with_metadata(self):
        """测试创建带元数据的响应步骤"""
        step = response_step(
            "根据检索结果...",
            sources=["sage_docs", "arxiv"],
            confidence=0.95,
        )

        assert step.metadata["sources"] == ["sage_docs", "arxiv"]
        assert step.metadata["confidence"] == 0.95


class TestModuleExports:
    """测试模块导出"""

    def test_import_from_models(self):
        """测试从 models 包导入"""
        from sage.studio.models import (
            AgentStep,
            StepStatus,
            StepType,
            reasoning_step,
            response_step,
            tool_call_step,
            tool_result_step,
        )

        # 验证导入成功
        assert StepType is not None
        assert StepStatus is not None
        assert AgentStep is not None
        assert reasoning_step is not None
        assert tool_call_step is not None
        assert tool_result_step is not None
        assert response_step is not None
