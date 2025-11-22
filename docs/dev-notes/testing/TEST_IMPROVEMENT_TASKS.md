# SAGE 测试覆盖率改进任务拆分

## 概述

当前系统测试覆盖率仅为 **37%**，需要大幅提升。本文档将测试改进工作拆分为3个相对独立的任务，可以并行分配给3个开发者同时进行。

**总体目标**: 将测试覆盖率从 37% 提升至 70%+

**拆分原则**:
- 按架构层级(L1-L6)和功能域划分
- 每个任务覆盖率独立计算，避免依赖冲突
- 优先测试关键路径和低覆盖率模块（0%-30%）
- 每个任务包含单元测试 + 集成测试

---

## 任务1: L1-L2层基础设施测试 (sage-common)

**负责人**: Developer A  
**预计工时**: 3-4周  
**当前覆盖率**: ~25%  
**目标覆盖率**: 75%+  
**预期提升**: 整体覆盖率 +15%

### 1.1 核心目标模块

#### 🔴 **高优先级 (0%-30% 覆盖率)**

1. **sage_embedding 嵌入服务组件** (当前 15%-40%)
   - 文件清单:
     ```
     packages/sage-common/src/sage/common/components/sage_embedding/
     ├── wrappers/
     │   ├── bedrock_wrapper.py      (40% → 80%)
     │   ├── cohere_wrapper.py        (53% → 85%)
     │   ├── hf_wrapper.py            (35% → 80%)
     │   ├── jina_wrapper.py          (41% → 80%)
     │   ├── nvidia_openai_wrapper.py (44% → 80%)
     │   ├── ollama_wrapper.py        (30% → 80%)
     │   ├── openai_wrapper.py        (38% → 80%)
     │   ├── siliconcloud_wrapper.py  (40% → 80%)
     │   ├── zhipu_wrapper.py         (51% → 85%)
     ├── service.py                   (19% → 75%)
     ├── embedding_model.py           (28% → 75%)
     ├── factory.py                   (72% → 90%)
     ```

   - **测试策略**:
     - Mock API调用（使用 `unittest.mock`, `responses`, `pytest-httpx`）
     - 测试初始化、配置验证、错误处理
     - 测试嵌入生成、批处理、重试逻辑
     - 集成测试: 不同wrapper的互换性

2. **sage_llm 推理服务** (当前 6%-35%)
   - 文件清单:
     ```
     packages/sage-common/src/sage/common/components/sage_llm/
     ├── sageLLM/control_plane/
     │   ├── manager.py               (6% → 70%)
     │   ├── router.py                (18% → 70%)
     │   ├── executors/
     │   │   ├── http_client.py       (14% → 70%)
     │   │   ├── local_async.py       (27% → 75%)
     │   ├── monitoring.py            (21% → 70%)
     │   ├── parallelism.py           (35% → 75%)
     │   ├── pd_routing.py            (19% → 70%)
     ├── control_plane_service.py     (30% → 75%)
     ├── service.py                   (20% → 75%)
     ```

   - **测试策略**:
     - Mock vLLM HTTP API
     - 测试请求路由、负载均衡、故障转移
     - 测试并行度控制、GPU分配
     - 集成测试: 完整推理流程模拟
     - **参考**: `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/tests/control_plane/conftest.py`

3. **utils 工具模块** (当前 0%-61%)
   - 文件清单:
     ```
     packages/sage-common/src/sage/common/utils/
     ├── config/
     │   ├── manager.py               (0% → 80%)
     ├── network/
     │   ├── base_tcp_client.py       (18% → 75%)
     │   ├── local_tcp_server.py      (0% → 70%)
     ├── serialization/
     │   ├── preprocessor.py          (0% → 75%)
     │   ├── ray_trimmer.py           (0% → 70%)
     │   ├── config.py                (0% → 75%)
     ├── system/
     │   ├── environment.py           (0% → 75%)
     │   ├── network.py               (10% → 75%)
     │   ├── process.py               (13% → 75%)
     ├── logging/
     │   ├── custom_logger.py         (55% → 85%)
     ```

   - **测试策略**:
     - Mock系统调用（socket, subprocess, os）
     - 测试配置加载、合并、验证
     - 测试序列化/反序列化边界情况
     - 测试日志格式化、输出
     - **参考**: `packages/sage-common/tests/unit/utils/config/test_loader.py`

#### 🟡 **中优先级 (30%-60% 覆盖率)**

4. **service 服务基类** (42%)
   ```
   packages/sage-common/src/sage/common/service/base_service.py (42% → 80%)
   ```

5. **model_registry 模型注册** (85%)
   ```
   packages/sage-common/src/sage/common/model_registry/vllm_registry.py (85% → 95%)
   ```

### 1.2 测试结构

```
packages/sage-common/tests/
├── unit/
│   ├── components/
│   │   ├── sage_embedding/
│   │   │   ├── test_wrappers.py           # 新增
│   │   │   ├── test_service.py            # 新增
│   │   │   ├── test_factory.py            # 扩展
│   │   │   └── conftest.py                # 新增fixtures
│   │   ├── sage_llm/
│   │   │   ├── test_control_plane.py      # 新增
│   │   │   ├── test_router.py             # 新增
│   │   │   ├── test_executors.py          # 新增
│   │   │   └── conftest.py                # 新增
│   ├── utils/
│   │   ├── config/
│   │   │   ├── test_manager.py            # 新增
│   │   ├── network/
│   │   │   ├── test_tcp_client.py         # 新增
│   │   │   ├── test_tcp_server.py         # 新增
│   │   ├── serialization/
│   │   │   ├── test_preprocessor.py       # 新增
│   │   │   ├── test_ray_trimmer.py        # 新增
│   │   ├── system/
│   │   │   ├── test_environment.py        # 新增
│   │   │   ├── test_process.py            # 新增
├── integration/
│   ├── test_embedding_service_integration.py  # 新增
│   ├── test_vllm_service_integration.py       # 新增
│   └── test_config_network_integration.py     # 新增
```

### 1.3 关键测试用例示例

#### Embedding Wrapper测试模板
```python
# packages/sage-common/tests/unit/components/sage_embedding/test_wrappers.py
import pytest
from unittest.mock import Mock, patch
from sage.common.components.sage_embedding.wrappers.openai_wrapper import OpenAIWrapper

@pytest.mark.unit
class TestOpenAIWrapper:
    def test_initialization_with_valid_config(self):
        """测试正确配置下的初始化"""
        wrapper = OpenAIWrapper(
            api_key="test-key",
            model_name="text-embedding-ada-002"
        )
        assert wrapper.model_name == "text-embedding-ada-002"

    @patch('openai.Embedding.create')
    def test_embed_documents_success(self, mock_create):
        """测试文档嵌入成功场景"""
        mock_create.return_value = Mock(
            data=[Mock(embedding=[0.1, 0.2, 0.3])]
        )

        wrapper = OpenAIWrapper(api_key="test-key")
        result = wrapper.embed_documents(["test doc"])

        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]

    @patch('openai.Embedding.create')
    def test_embed_documents_with_retry(self, mock_create):
        """测试重试逻辑"""
        mock_create.side_effect = [
            Exception("Rate limit"),
            Mock(data=[Mock(embedding=[0.1, 0.2])])
        ]

        wrapper = OpenAIWrapper(api_key="test-key", max_retries=2)
        result = wrapper.embed_documents(["test"])

        assert len(result) == 1
        assert mock_create.call_count == 2
```

#### vLLM Router测试模板
```python
# packages/sage-common/tests/unit/components/sage_llm/test_router.py
import pytest
from unittest.mock import AsyncMock, patch
from sage.common.components.sage_llm.sageLLM.control_plane.router import Router

@pytest.mark.unit
@pytest.mark.asyncio
class TestRouter:
    async def test_route_request_to_available_instance(self):
        """测试请求路由到可用实例"""
        router = Router(policy="round_robin")

        # Mock instances
        instance1 = Mock(id="inst-1", is_available=True)
        instance2 = Mock(id="inst-2", is_available=False)
        router._instances = [instance1, instance2]

        selected = await router.route_request({"prompt": "test"})
        assert selected.id == "inst-1"

    async def test_route_request_no_available_instance(self):
        """测试无可用实例时的处理"""
        router = Router()
        router._instances = []

        with pytest.raises(RuntimeError, match="No available instances"):
            await router.route_request({"prompt": "test"})
```

### 1.4 工作检查清单

- [ ] 为所有 wrapper 创建 Mock 测试（9个wrapper）
- [ ] 实现 embedding service 集成测试
- [ ] 完成 vLLM control plane 单元测试
- [ ] 实现 vLLM 异步执行器测试
- [ ] 完成 config manager 测试
- [ ] 实现 TCP client/server Mock测试
- [ ] 完成 serialization 边界测试
- [ ] 实现 system utils Mock测试
- [ ] 运行覆盖率报告并验证达标

---

## 任务2: L3-L4层核心引擎测试 (sage-kernel + sage-middleware部分)

**负责人**: Developer B  
**预计工时**: 4-5周  
**当前覆盖率**: ~35%  
**目标覆盖率**: 75%+  
**预期提升**: 整体覆盖率 +18%

### 2.1 核心目标模块

#### 🔴 **高优先级 (0%-40% 覆盖率)**

1. **sage-kernel 运行时核心** (当前 10%-60%)
   - 文件清单:
     ```
     packages/sage-kernel/src/sage/kernel/
     ├── runtime/
     │   ├── dispatcher.py                   (51% → 85%)
     │   ├── job_manager.py                  (47% → 80%)
     │   ├── job_manager_server.py           (22% → 75%)
     │   ├── jobmanager_client.py            (36% → 75%)
     │   ├── heartbeat_monitor.py            (10% → 70%)
     │   ├── service/
     │   │   ├── base_service_task.py        (49% → 80%)
     │   │   ├── ray_service_task.py         (0% → 70%)
     │   │   ├── service_caller.py           (60% → 85%)
     │   ├── task/
     │   │   ├── base_task.py                (49% → 80%)
     │   │   ├── ray_task.py                 (56% → 80%)
     │   ├── communication/
     │   │   ├── rpc/rpc_queue.py            (27% → 75%)
     │   ├── monitoring/
     │   │   ├── metrics_reporter.py         (14% → 70%)
     ```

   - **测试策略**:
     - Mock Ray Actor/分布式调用
     - 测试任务调度、执行、失败恢复
     - 测试心跳监控、超时处理
     - 测试RPC通信、消息队列
     - 集成测试: 端到端任务执行流程

2. **sage-kernel API层** (当前 11%-60%)
   - 文件清单:
     ```
     packages/sage-kernel/src/sage/kernel/api/
     ├── base_environment.py                 (53% → 80%)
     ├── local_environment.py                (47% → 80%)
     ├── remote_environment.py               (11% → 70%)
     ├── connected_streams.py                (37% → 75%)
     ├── datastream.py                       (60% → 85%)
     ├── operator/
     │   ├── base_operator.py                (37% → 75%)
     │   ├── comap_operator.py               (26% → 75%)
     │   ├── filter_operator.py              (26% → 75%)
     │   ├── flatmap_operator.py             (17% → 75%)
     │   ├── join_operator.py                (11% → 70%)
     │   ├── keyby_operator.py               (25% → 75%)
     │   ├── source_operator.py              (17% → 70%)
     ├── function/
     │   ├── simple_batch_function.py        (26% → 75%)
     ├── service/
     │   ├── base_service.py                 (0% → 75%)
     │   ├── pipeline_service/               (0% → 70%)
     ```

   - **测试策略**:
     - 测试 Environment 创建、配置
     - 测试 DataStream API 链式调用
     - 测试各类 Operator 的数据处理逻辑
     - 测试本地/远程执行切换
     - 集成测试: 完整 Pipeline 执行
     - **参考**: `packages/sage-kernel/tests/unit/core/conftest.py` 中的 `IntegrationTestHelper`

3. **sage-kernel 容错机制** (当前 17%-64%)
   - 文件清单:
     ```
     packages/sage-kernel/src/sage/kernel/fault_tolerance/
     ├── impl/
     │   ├── checkpoint_impl.py              (19% → 75%)
     │   ├── checkpoint_recovery.py          (17% → 70%)
     │   ├── restart_recovery.py             (31% → 75%)
     │   ├── restart_strategy.py             (54% → 80%)
     │   ├── lifecycle_impl.py               (55% → 80%)
     ├── factory.py                          (33% → 75%)
     ```

   - **测试策略**:
     - Mock 检查点存储（文件系统/数据库）
     - 测试故障检测、重启策略
     - 测试状态恢复、数据一致性
     - 集成测试: 模拟故障场景

4. **sage-middleware 中间件算法** (当前 20%-32%)
   - 文件清单:
     ```
     packages/sage-middleware/src/sage/middleware/components/
     ├── sage_tsdb/python/
     │   ├── algorithms/
     │   │   ├── out_of_order_join.py        (32% → 75%)
     │   │   ├── window_aggregator.py        (20% → 75%)
     │   ├── sage_tsdb.py                    (29% → 75%)
     │   ├── micro_service/sage_tsdb_service.py (32% → 75%)
     ├── sage_flow/python/
     │   ├── sage_flow.py                    (58% → 85%)
     │   ├── micro_service/sage_flow_service.py (0% → 70%)
     ```

   - **测试策略**:
     - 测试时序数据乱序Join算法
     - 测试窗口聚合逻辑
     - 测试流式处理边界条件
     - 集成测试: 完整TSDB流程

#### 🟡 **中优先级**

5. **sage-kernel 调度器** (当前 72%-95%)
   ```
   packages/sage-kernel/src/sage/kernel/scheduler/
   ├── node_selector.py                    (72% → 85%)
   ├── impl/resource_aware_scheduler.py    (90% → 95%)
   ```

### 2.2 测试结构

```
packages/sage-kernel/tests/
├── unit/
│   ├── runtime/
│   │   ├── test_dispatcher.py              # 扩展
│   │   ├── test_job_manager.py             # 新增
│   │   ├── test_heartbeat_monitor.py       # 新增
│   │   ├── service/
│   │   │   ├── test_service_task.py        # 新增
│   │   │   ├── test_ray_service_task.py    # 新增
│   │   ├── task/
│   │   │   ├── test_base_task.py           # 扩展
│   │   │   ├── test_ray_task.py            # 扩展
│   ├── api/
│   │   ├── test_environments.py            # 扩展
│   │   ├── test_operators.py               # 新增
│   │   ├── test_service.py                 # 新增
│   ├── fault_tolerance/
│   │   ├── test_checkpoint.py              # 新增
│   │   ├── test_recovery.py                # 新增
│   │   └── conftest.py                     # 新增fixtures
├── integration/
│   ├── test_pipeline_execution.py          # 扩展
│   ├── test_fault_tolerance_e2e.py         # 新增
│   ├── test_distributed_task.py            # 新增

packages/sage-middleware/tests/
├── components/
│   ├── sage_tsdb/
│   │   ├── test_algorithms.py              # 新增
│   │   ├── test_service.py                 # 新增
│   ├── sage_flow/
│   │   ├── test_flow_service.py            # 新增
```

### 2.3 关键测试用例示例

#### Dispatcher测试模板
```python
# packages/sage-kernel/tests/unit/runtime/test_dispatcher.py
import pytest
from unittest.mock import Mock, AsyncMock
from sage.kernel.runtime.dispatcher import Dispatcher

@pytest.mark.unit
class TestDispatcher:
    def test_dispatch_task_to_local(self):
        """测试本地任务分发"""
        dispatcher = Dispatcher()
        task = Mock(spec=['execute'], name="test_task")
        task.execute = Mock(return_value="result")

        result = dispatcher.dispatch(task, mode="local")
        assert result == "result"
        task.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_task_to_remote_ray(self):
        """测试Ray远程任务分发"""
        dispatcher = Dispatcher()

        with patch('ray.remote') as mock_ray:
            mock_remote_fn = AsyncMock(return_value="remote_result")
            mock_ray.return_value.remote = mock_remote_fn

            result = await dispatcher.dispatch_async(
                task=Mock(),
                mode="ray"
            )
            assert result == "remote_result"
```

#### Fault Tolerance测试模板
```python
# packages/sage-kernel/tests/unit/fault_tolerance/test_checkpoint.py
import pytest
from unittest.mock import Mock, patch
from sage.kernel.fault_tolerance.impl.checkpoint_impl import CheckpointImpl

@pytest.mark.unit
class TestCheckpointImpl:
    def test_save_checkpoint_success(self, tmp_path):
        """测试检查点保存成功"""
        checkpoint = CheckpointImpl(storage_path=str(tmp_path))

        state = {"counter": 42, "data": [1, 2, 3]}
        checkpoint_id = checkpoint.save(state)

        assert checkpoint_id is not None
        assert (tmp_path / f"{checkpoint_id}.ckpt").exists()

    def test_restore_checkpoint_success(self, tmp_path):
        """测试检查点恢复"""
        checkpoint = CheckpointImpl(storage_path=str(tmp_path))

        original_state = {"key": "value"}
        ckpt_id = checkpoint.save(original_state)

        restored_state = checkpoint.restore(ckpt_id)
        assert restored_state == original_state

    def test_checkpoint_cleanup_old_checkpoints(self, tmp_path):
        """测试旧检查点清理"""
        checkpoint = CheckpointImpl(
            storage_path=str(tmp_path),
            max_checkpoints=2
        )

        # 创建3个检查点
        for i in range(3):
            checkpoint.save({"version": i})

        # 验证只保留最新的2个
        checkpoints = list(tmp_path.glob("*.ckpt"))
        assert len(checkpoints) == 2
```

### 2.4 工作检查清单

- [ ] 实现 Dispatcher 完整单元测试
- [ ] 完成 JobManager 测试（含Ray Mock）
- [ ] 实现心跳监控测试
- [ ] 完成 RPC Queue 测试
- [ ] 实现所有 Operator 测试（9个operator）
- [ ] 完成 Environment API 测试
- [ ] 实现 checkpoint/recovery 完整测试
- [ ] 完成 TSDB 算法测试
- [ ] 实现端到端 Pipeline 集成测试
- [ ] 运行覆盖率报告并验证达标

---

## 任务3: L4-L6层应用与算法测试 (sage-middleware RAG + sage-libs)

**负责人**: Developer C  
**预计工时**: 3-4周  
**当前覆盖率**: ~25%  
**目标覆盖率**: 70%+  
**预期提升**: 整体覆盖率 +12%

### 3.1 核心目标模块

#### 🔴 **高优先级 (0%-50% 覆盖率)**

1. **sage-middleware RAG组件** (当前 11%-92%)
   - 文件清单:
     ```
     packages/sage-middleware/src/sage/middleware/operators/
     ├── rag/
     │   ├── retriever.py                    (50% → 85%)
     │   ├── reranker.py                     (47% → 80%)
     │   ├── promptor.py                     (61% → 85%)
     │   ├── refiner.py                      (88% → 95%)
     │   ├── generator.py                    (92% → 98%)
     │   ├── evaluate.py                     (92% → 98%)
     │   ├── arxiv.py                        (57% → 85%)
     ├── filters/
     │   ├── context_source.py               (15% → 75%)
     │   ├── evaluate_filter.py              (21% → 75%)
     │   ├── tool_filter.py                  (19% → 75%)
     ├── llm/
     │   ├── vllm_generator.py               (36% → 75%)
     ├── tools/
     │   ├── searcher_tool.py                (11% → 70%)
     │   ├── arxiv_paper_searcher.py         (22% → 75%)
     │   ├── nature_news_fetcher.py          (43% → 75%)
     │   ├── text_detector.py                (39% → 75%)
     │   ├── url_text_extractor.py           (50% → 80%)
     ```

   - **测试策略**:
     - Mock 向量数据库（FAISS/Milvus/Chroma）
     - Mock LLM API调用
     - 测试检索、重排序、提示生成逻辑
     - 测试评估指标计算
     - 集成测试: 完整RAG Pipeline
     - **参考**: `packages/sage-middleware/tests/operators/rag/` 现有测试

2. **sage-middleware 内存管理 (NeuroMem)** (当前 9%-80%)
   - 文件清单:
     ```
     packages/sage-middleware/src/sage/middleware/components/sage_mem/
     ├── neuromem/
     │   ├── memory_manager.py               (39% → 75%)
     │   ├── memory_collection/
     │   │   ├── kv_collection.py            (9% → 70%)
     │   │   ├── vdb_collection.py           (44% → 80%)
     │   │   ├── base_collection.py          (32% → 75%)
     │   ├── search_engine/
     │   │   ├── vdb_index/faiss_index.py    (35% → 75%)
     │   │   ├── kv_index/bm25s_index.py     (14% → 70%)
     │   ├── storage_engine/
     │   │   ├── metadata_storage.py         (46% → 75%)
     │   │   ├── text_storage.py             (47% → 75%)
     │   │   ├── vector_storage.py           (0% → 70%)
     ├── services/
     │   ├── neuromem_vdb.py                 (11% → 70%)
     │   ├── short_term_memory_service.py    (0% → 70%)
     ```

   - **测试策略**:
     - Mock FAISS/BM25索引
     - 测试内存集合CRUD操作
     - 测试索引构建、搜索
     - 测试存储引擎持久化
     - 集成测试: 完整内存管理流程

3. **sage-libs 算法库 (全0%覆盖率!)**
   - 文件清单:
     ```
     packages/sage-libs/src/sage/libs/
     ├── agentic/                            # 全部 0% → 70%
     │   ├── agents/agent.py
     │   ├── agents/bots/
     │   ├── workflow/base.py
     │   ├── workflow/evaluator.py
     │   ├── workflow/constraints.py
     ├── foundation/                         # 全部 0% → 70%
     │   ├── context/compression/
     │   ├── io/source.py
     │   ├── io/sink.py
     │   ├── io/batch.py
     │   ├── tools/tool.py
     ├── privacy/unlearning/                 # 全部 0% → 70%
     │   ├── algorithms/
     │   ├── dp_unlearning/
     │   ├── evaluation/metrics.py
     ├── integrations/                       # 全部 0% → 60%
     │   ├── chroma.py
     │   ├── milvus.py
     │   ├── huggingface.py
     │   ├── openai.py
     ├── rag/                                # 全部 0% → 60%
     │   ├── chunk.py
     │   ├── document_loaders.py
     │   ├── types.py
     ```

   - **测试策略**:
     - Mock 外部集成（OpenAI, HuggingFace, Chroma等）
     - 测试Agent工作流逻辑
     - 测试隐私卸载算法正确性
     - 测试数据加载、分块
     - **注意**: 这是覆盖率提升的最大增长点

4. **sage-middleware Context管理** (当前 20%-83%)
   - 文件清单:
     ```
     packages/sage-middleware/src/sage/middleware/context/
     ├── model_context.py                    (20% → 75%)
     ├── search_session.py                   (49% → 80%)
     ├── search_query_results.py             (74% → 90%)
     ```

### 3.2 测试结构

```
packages/sage-middleware/tests/
├── operators/
│   ├── rag/
│   │   ├── test_retriever.py               # 扩展
│   │   ├── test_reranker.py                # 扩展
│   │   ├── test_promptor.py                # 扩展
│   │   ├── test_arxiv.py                   # 新增
│   ├── filters/
│   │   ├── test_context_source.py          # 新增
│   │   ├── test_filters.py                 # 新增
│   ├── llm/
│   │   ├── test_vllm_generator.py          # 新增
│   ├── tools/
│   │   ├── test_searcher_tool.py           # 新增
│   │   ├── test_arxiv_searcher.py          # 新增
├── components/
│   ├── sage_mem/
│   │   ├── test_memory_manager.py          # 新增
│   │   ├── test_collections.py             # 新增
│   │   ├── test_search_engine.py           # 新增
│   │   ├── test_storage_engine.py          # 新增
│   ├── sage_refiner/
│   │   ├── test_adapter.py                 # 新增
│   │   ├── test_service.py                 # 扩展
├── context/
│   ├── test_model_context.py               # 新增
│   ├── test_search_session.py              # 新增
├── integration/
│   ├── test_rag_pipeline_e2e.py            # 扩展
│   ├── test_memory_integration.py          # 新增

packages/sage-libs/tests/
├── lib/
│   ├── agentic/
│   │   ├── agents/
│   │   │   ├── test_agent.py               # 扩展
│   │   │   ├── test_bots.py                # 新增
│   │   ├── workflow/
│   │   │   ├── test_workflow.py            # 新增
│   │   │   ├── test_evaluator.py           # 新增
│   ├── foundation/
│   │   ├── context/
│   │   │   ├── test_compression.py         # 新增
│   │   ├── io/
│   │   │   ├── test_source.py              # 新增
│   │   │   ├── test_sink.py                # 新增
│   │   ├── tools/
│   │   │   ├── test_tool.py                # 新增
│   ├── privacy/
│   │   ├── test_gaussian_unlearning.py     # 新增
│   │   ├── test_dp_unlearning.py           # 新增
│   │   ├── test_metrics.py                 # 新增
│   ├── integrations/
│   │   ├── test_chroma.py                  # 新增
│   │   ├── test_milvus.py                  # 新增
│   │   ├── test_openai.py                  # 新增
│   ├── rag/
│   │   ├── test_chunk.py                   # 新增
│   │   ├── test_document_loaders.py        # 新增
```

### 3.3 关键测试用例示例

#### RAG Retriever测试模板
```python
# packages/sage-middleware/tests/operators/rag/test_retriever.py
import pytest
from unittest.mock import Mock, patch
from sage.middleware.operators.rag.retriever import VectorRetriever

@pytest.mark.unit
class TestVectorRetriever:
    def test_initialization_with_faiss_backend(self):
        """测试FAISS后端初始化"""
        retriever = VectorRetriever(
            backend="faiss",
            embedding_model="mock-model"
        )
        assert retriever.backend == "faiss"

    @patch('sage.middleware.components.sage_mem.neuromem.search_engine.vdb_index.faiss_index.FaissIndex')
    def test_retrieve_documents_top_k(self, mock_faiss):
        """测试Top-K文档检索"""
        # Mock search results
        mock_faiss.return_value.search.return_value = [
            {"id": "doc1", "score": 0.95, "content": "text1"},
            {"id": "doc2", "score": 0.85, "content": "text2"}
        ]

        retriever = VectorRetriever(backend="faiss")
        results = retriever.retrieve("query text", top_k=2)

        assert len(results) == 2
        assert results[0]["score"] > results[1]["score"]

    @pytest.mark.asyncio
    async def test_retrieve_with_filter(self):
        """测试带过滤条件的检索"""
        retriever = VectorRetriever(backend="faiss")

        results = await retriever.retrieve_async(
            query="test",
            filters={"category": "tech"},
            top_k=5
        )
        assert isinstance(results, list)
```

#### Agent Workflow测试模板
```python
# packages/sage-libs/tests/lib/agentic/workflow/test_workflow.py
import pytest
from unittest.mock import Mock, patch
from sage.libs.agentic.workflow.base import Workflow

@pytest.mark.unit
class TestWorkflow:
    def test_workflow_initialization(self):
        """测试工作流初始化"""
        workflow = Workflow(
            name="test_workflow",
            steps=["step1", "step2"]
        )
        assert workflow.name == "test_workflow"
        assert len(workflow.steps) == 2

    @patch('sage.libs.agentic.agents.agent.Agent')
    def test_workflow_execution(self, mock_agent):
        """测试工作流执行"""
        mock_agent_instance = Mock()
        mock_agent_instance.execute.return_value = "result"
        mock_agent.return_value = mock_agent_instance

        workflow = Workflow(steps=["step1"])
        result = workflow.run(input_data={"query": "test"})

        assert result is not None
        mock_agent_instance.execute.assert_called()

    def test_workflow_with_constraints(self):
        """测试带约束条件的工作流"""
        from sage.libs.agentic.workflow.constraints import TimeConstraint

        constraint = TimeConstraint(max_seconds=10)
        workflow = Workflow(
            steps=["step1"],
            constraints=[constraint]
        )

        assert len(workflow.constraints) == 1
```

#### Privacy Unlearning测试模板
```python
# packages/sage-libs/tests/lib/privacy/test_gaussian_unlearning.py
import pytest
import numpy as np
from sage.libs.privacy.unlearning.algorithms.gaussian_unlearning import GaussianUnlearning

@pytest.mark.unit
class TestGaussianUnlearning:
    def test_gaussian_mechanism_adds_noise(self):
        """测试高斯机制添加噪声"""
        unlearning = GaussianUnlearning(epsilon=1.0, delta=1e-5)

        original_data = np.array([1.0, 2.0, 3.0])
        noisy_data = unlearning.add_noise(original_data)

        # 验证添加了噪声
        assert not np.array_equal(original_data, noisy_data)
        # 验证维度不变
        assert noisy_data.shape == original_data.shape

    def test_unlearning_preserves_privacy_budget(self):
        """测试卸载操作保持隐私预算"""
        unlearning = GaussianUnlearning(epsilon=1.0)

        data = np.random.rand(100, 10)
        unlearn_indices = [0, 1, 2]

        result = unlearning.unlearn(data, unlearn_indices)

        assert result.privacy_budget_used <= 1.0
        assert len(result.remaining_data) == len(data) - len(unlearn_indices)
```

### 3.4 工作检查清单

- [ ] 实现 Retriever 完整测试（含多后端）
- [ ] 完成 Reranker 测试
- [ ] 实现 RAG Promptor 测试
- [ ] 完成 RAG工具（Arxiv等）测试
- [ ] 实现 NeuroMem 内存管理测试
- [ ] 完成搜索引擎索引测试
- [ ] 实现存储引擎测试
- [ ] 完成 Agent 工作流测试
- [ ] 实现隐私卸载算法测试
- [ ] 完成所有 integrations 测试
- [ ] 实现 RAG 端到端集成测试
- [ ] 运行覆盖率报告并验证达标

---

## 通用测试规范

### 测试标记 (Pytest Marks)

所有测试必须使用以下标记之一：

```python
@pytest.mark.unit           # 单元测试（快速，无外部依赖）
@pytest.mark.integration    # 集成测试（可能涉及多模块）
@pytest.mark.external       # 外部API测试（需要真实API key）
@pytest.mark.slow           # 慢速测试
@pytest.mark.asyncio        # 异步测试
```

### Mock策略

1. **API调用**: 使用 `responses`, `pytest-httpx`, `aioresponses`
2. **文件系统**: 使用 `tmp_path` fixture
3. **Ray/分布式**: 使用 `unittest.mock.AsyncMock`
4. **LLM调用**: Mock返回预定义结果
5. **数据库**: 使用内存数据库或Mock

### Fixtures管理

在各包的 `conftest.py` 中定义共享fixtures：

```python
# packages/*/tests/conftest.py
import pytest

@pytest.fixture
def mock_embedding_model():
    """Mock embedding model fixture"""
    model = Mock()
    model.embed.return_value = [[0.1] * 768]
    return model

@pytest.fixture
def temp_vector_db(tmp_path):
    """Temporary vector database fixture"""
    db_path = tmp_path / "test_db"
    db_path.mkdir()
    return str(db_path)
```

### 覆盖率验证

每个任务完成后，运行：

```bash
# 针对特定包
sage-dev project test --coverage --package sage-common
sage-dev project test --coverage --package sage-kernel
sage-dev project test --coverage --package sage-middleware
sage-dev project test --coverage --package sage-libs

# 验证覆盖率报告
cat coverage.xml | grep 'line-rate'
```

---

## 任务协调

### 依赖关系
- 任务1、2、3 **相互独立**，可并行开发
- 各任务覆盖不同文件，无代码冲突
- 共用 `conftest.py` fixtures时需协调

### 代码审查清单
- [ ] 所有测试通过 `pytest` 执行
- [ ] 覆盖率达到目标（用 `pytest-cov` 验证）
- [ ] Mock使用正确，无真实API调用
- [ ] 测试命名清晰，遵循 `test_<function>_<scenario>_<expected>`
- [ ] 集成测试有清晰的场景描述
- [ ] 异步测试使用 `@pytest.mark.asyncio`
- [ ] 代码通过 `sage-dev quality --check-only`

### 提交规范
- 提交信息格式: `test(<scope>): <description>`
- 示例: `test(sage-common): add embedding wrappers unit tests`
- PR标题: `[Test] <Task Name> - <Module Coverage Improvement>`

---

## 预期成果

### 各任务覆盖率提升目标

| 任务 | 包 | 当前覆盖率 | 目标覆盖率 | 提升幅度 |
|------|------|-----------|-----------|---------|
| 任务1 | sage-common | ~25% | 75%+ | +50% |
| 任务2 | sage-kernel | ~35% | 75%+ | +40% |
| 任务2 | sage-middleware(部分) | ~30% | 75%+ | +45% |
| 任务3 | sage-libs | ~0% | 70%+ | +70% |
| 任务3 | sage-middleware(RAG) | ~50% | 85%+ | +35% |

### 整体系统覆盖率预期

- **当前**: 37%
- **任务1完成后**: ~52%
- **任务2完成后**: ~70%
- **任务3完成后**: **~82%** ✅

---

## 参考资源

### 现有测试示例
- `packages/sage-middleware/tests/operators/rag/test_evaluate.py` - RAG评估测试
- `packages/sage-common/tests/unit/utils/config/test_loader.py` - 配置加载测试
- `packages/sage-kernel/tests/unit/core/conftest.py` - Kernel测试fixtures
- `packages/sage-libs/tests/lib/agents/test_agent.py` - Agent测试

### 开发文档
- `DEVELOPER.md` - 开发者指南
- `CONTRIBUTING.md` - 贡献指南
- `docs/dev-notes/cross-layer/ci-cd/testing.md` - 测试文档
- `tools/pytest.ini` - Pytest配置

### Mock工具
- `unittest.mock` - Python标准库
- `pytest-mock` - Pytest mock插件
- `responses` - HTTP Mock
- `pytest-httpx` - HTTPX Mock
- `aioresponses` - Async HTTP Mock
- `pytest-asyncio` - 异步测试

### CI/CD参考
- `.github/workflows/build-test.yml` - CI测试流程
- `tools/pre-commit-config.yaml` - 预提交检查

---

## 附录: 快速启动命令

```bash
# 环境准备
./quickstart.sh --dev --yes

# 运行特定任务的测试
# 任务1
pytest packages/sage-common/tests/unit/components/sage_embedding/ -v
pytest packages/sage-common/tests/unit/components/sage_llm/ -v
pytest packages/sage-common/tests/unit/utils/ -v --cov=sage.common.utils

# 任务2
pytest packages/sage-kernel/tests/unit/runtime/ -v --cov=sage.kernel.runtime
pytest packages/sage-kernel/tests/unit/api/ -v --cov=sage.kernel.api
pytest packages/sage-middleware/tests/components/sage_tsdb/ -v

# 任务3
pytest packages/sage-middleware/tests/operators/rag/ -v --cov=sage.middleware.operators.rag
pytest packages/sage-libs/tests/ -v --cov=sage.libs

# 覆盖率报告
sage-dev project test --coverage --package <package-name>
```

---

**最后更新**: 2025-11-20  
**文档版本**: 1.0  
**维护者**: SAGE Team
