/**
 * @file test_stream_engine.cpp
 * @brief 流引擎单元测试
 *
 * 测试 StreamEngine, ExecutionGraph 等流处理核心组件
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <memory>
#include <vector>
#include <string>
#include <chrono>
#include <thread>
#include <iostream>

// Engine 组件头文件
#include "engine/stream_engine.hpp"
#include "engine/execution_graph.hpp"
#include "engine/stream_engine_config.hpp"
#include "engine/stream_engine_enums.hpp"
#include "engine/stream_engine_metrics.hpp"

// Operator 组件头文件
#include "operator/base_operator.hpp"
#include "operator/source_operator.hpp"
#include "operator/response.hpp"

// Message 组件头文件
#include "message/multimodal_message.hpp"
#include "message/content_type.hpp"

namespace sage_flow {

// =============================================================================
// 测试用例类定义
// =============================================================================

// Mock Source Operator for testing
class MockSourceOperator : public SourceOperator {
public:
    explicit MockSourceOperator(std::string name, std::vector<std::string> messages)
        : SourceOperator(std::move(name)), messages_(std::move(messages)), index_(0) {}

    auto hasNext() -> bool override {
        return index_ < messages_.size();
    }

    auto next() -> std::unique_ptr<MultiModalMessage> override {
        if (!hasNext()) return nullptr;

        auto message = std::make_unique<MultiModalMessage>(
            static_cast<uint64_t>(index_), ContentType::kText, messages_[index_]);
        index_++;
        return message;
    }

    auto reset() -> void override {
        index_ = 0;
    }

private:
    std::vector<std::string> messages_;
    size_t index_;
};

// Mock Sink Operator for testing
class MockSinkOperator : public BaseOperator {
public:
    explicit MockSinkOperator(std::string name)
        : BaseOperator(OperatorType::kSink, std::move(name)) {}

    auto process(Response& input_record, int slot) -> bool override {
        if (input_record.hasMessage()) {
            auto message = input_record.getMessage();
            if (message) {
                received_messages_.push_back(message->getContentAsString());
                return true;
            }
        }
        return false;
    }

    const std::vector<std::string>& getReceivedMessages() const {
        return received_messages_;
    }

    void clearMessages() {
        received_messages_.clear();
    }

private:
    std::vector<std::string> received_messages_;
};

// Mock Filter Operator for testing
class MockFilterOperator : public BaseOperator {
public:
    explicit MockFilterOperator(std::string name, std::string filter_keyword)
        : BaseOperator(OperatorType::kFilter, std::move(name)),
          filter_keyword_(std::move(filter_keyword)) {}

    auto process(Response& input_record, int slot) -> bool override {
        if (input_record.hasMessage()) {
            auto message = input_record.getMessage();
            if (message) {
                std::string content = message->getContentAsString();
                if (content.find(filter_keyword_) != std::string::npos) {
                    // Create new response with filtered message
                    Response output_response(std::move(message));
                    emit(0, output_response);
                    return true;
                }
            }
        }
        return false;
    }

private:
    std::string filter_keyword_;
};

// =============================================================================
// ExecutionGraph 测试
// =============================================================================

TEST(ExecutionGraphTest, Constructor) {
    auto graph = std::make_shared<ExecutionGraph>();
    EXPECT_TRUE(graph->empty());
    EXPECT_EQ(graph->size(), 0);
    EXPECT_TRUE(graph->isValid());
}

TEST(ExecutionGraphTest, AddOperator) {
    auto graph = std::make_shared<ExecutionGraph>();
    auto op = std::make_shared<MockSourceOperator>("test_source", std::vector<std::string>{"msg1"});

    auto op_id = graph->addOperator(op);
    EXPECT_EQ(op_id, 0);
    EXPECT_EQ(graph->size(), 1);
    EXPECT_FALSE(graph->empty());
}

TEST(ExecutionGraphTest, ConnectOperators) {
    auto graph = std::make_shared<ExecutionGraph>();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"msg1"});
    auto sink_op = std::make_shared<MockSinkOperator>("sink");

    auto source_id = graph->addOperator(source_op);
    auto sink_id = graph->addOperator(sink_op);

    graph->connectOperators(source_id, sink_id);

    auto successors = graph->getSuccessors(source_id);
    auto predecessors = graph->getPredecessors(sink_id);

    EXPECT_EQ(successors.size(), 1);
    EXPECT_EQ(successors[0], sink_id);
    EXPECT_EQ(predecessors.size(), 1);
    EXPECT_EQ(predecessors[0], source_id);
}

TEST(ExecutionGraphTest, TopologicalOrder) {
    auto graph = std::make_shared<ExecutionGraph>();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"msg1"});
    auto filter_op = std::make_shared<MockFilterOperator>("filter", "msg");
    auto sink_op = std::make_shared<MockSinkOperator>("sink");

    auto source_id = graph->addOperator(source_op);
    auto filter_id = graph->addOperator(filter_op);
    auto sink_id = graph->addOperator(sink_op);

    graph->connectOperators(source_id, filter_id);
    graph->connectOperators(filter_id, sink_id);

    auto topo_order = graph->getTopologicalOrder();
    EXPECT_EQ(topo_order.size(), 3);
    EXPECT_EQ(topo_order[0], source_id);
    EXPECT_EQ(topo_order[1], filter_id);
    EXPECT_EQ(topo_order[2], sink_id);
}

TEST(ExecutionGraphTest, SourceAndSinkOperators) {
    auto graph = std::make_shared<ExecutionGraph>();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"msg1"});
    auto filter_op = std::make_shared<MockFilterOperator>("filter", "msg");
    auto sink_op = std::make_shared<MockSinkOperator>("sink");

    auto source_id = graph->addOperator(source_op);
    auto filter_id = graph->addOperator(filter_op);
    auto sink_id = graph->addOperator(sink_op);

    graph->connectOperators(source_id, filter_id);
    graph->connectOperators(filter_id, sink_id);

    auto sources = graph->getSourceOperators();
    auto sinks = graph->getSinkOperators();

    EXPECT_EQ(sources.size(), 1);
    EXPECT_EQ(sources[0], source_id);
    EXPECT_EQ(sinks.size(), 1);
    EXPECT_EQ(sinks[0], sink_id);
}

TEST(ExecutionGraphTest, RemoveOperator) {
    auto graph = std::make_shared<ExecutionGraph>();
    auto op = std::make_shared<MockSourceOperator>("test", std::vector<std::string>{"msg1"});

    auto op_id = graph->addOperator(op);
    EXPECT_EQ(graph->size(), 1);

    graph->removeOperator(op_id);
    EXPECT_EQ(graph->size(), 0);
    EXPECT_TRUE(graph->empty());
}

TEST(ExecutionGraphTest, Validation) {
    auto graph = std::make_shared<ExecutionGraph>();
    EXPECT_TRUE(graph->isValid());
    EXPECT_TRUE(graph->validate());

    // Add operators and connections
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"msg1"});
    auto sink_op = std::make_shared<MockSinkOperator>("sink");

    auto source_id = graph->addOperator(source_op);
    auto sink_id = graph->addOperator(sink_op);
    graph->connectOperators(source_id, sink_id);

    EXPECT_TRUE(graph->isValid());
}

// =============================================================================
// StreamEngine 基本功能测试
// =============================================================================

TEST(StreamEngineTest, Constructor) {
    StreamEngine engine;
    EXPECT_FALSE(engine.isRunning());
    EXPECT_FALSE(engine.isPaused());
}

TEST(StreamEngineTest, ConstructorWithMode) {
    StreamEngine engine(ExecutionMode::MULTI_THREADED);
    EXPECT_EQ(engine.getExecutionMode(), ExecutionMode::MULTI_THREADED);
}

TEST(StreamEngineTest, ConstructorWithConfig) {
    EngineConfig config;
    config.execution_mode = ExecutionMode::ASYNC;
    config.thread_pool_size = 8;

    StreamEngine engine(config);
    EXPECT_EQ(engine.getExecutionMode(), ExecutionMode::ASYNC);
    EXPECT_EQ(engine.getThreadCount(), 8);
}

TEST(StreamEngineTest, CreateGraph) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    EXPECT_TRUE(graph != nullptr);
    EXPECT_TRUE(graph->empty());
}

TEST(StreamEngineTest, SubmitGraph) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);
    EXPECT_EQ(graph_id, 0);

    auto submitted_graphs = engine.getSubmittedGraphs();
    EXPECT_EQ(submitted_graphs.size(), 1);
    EXPECT_EQ(submitted_graphs[0], graph_id);
}

TEST(StreamEngineTest, ExecuteSimpleGraph) {
    StreamEngine engine;
    auto graph = engine.createGraph();

    // Create source and sink operators
    auto source_op = std::make_shared<MockSourceOperator>("source",
        std::vector<std::string>{"message1", "message2"});
    auto sink_op = std::make_shared<MockSinkOperator>("sink");

    auto source_id = graph->addOperator(source_op);
    auto sink_id = graph->addOperator(sink_op);
    graph->connectOperators(source_id, sink_id);

    // Submit and execute
    auto graph_id = engine.submitGraph(graph);
    engine.executeGraph(graph_id);

    // Check results
    auto sink_op_ptr = std::dynamic_pointer_cast<MockSinkOperator>(
        graph->getOperator(sink_id));
    ASSERT_TRUE(sink_op_ptr != nullptr);

    const auto& received = sink_op_ptr->getReceivedMessages();
    EXPECT_EQ(received.size(), 2);
    EXPECT_EQ(received[0], "message1");
    EXPECT_EQ(received[1], "message2");
}

TEST(StreamEngineTest, ExecuteGraphWithFilter) {
    StreamEngine engine;
    auto graph = engine.createGraph();

    // Create operators
    auto source_op = std::make_shared<MockSourceOperator>("source",
        std::vector<std::string>{"important: msg1", "normal: msg2", "important: msg3"});
    auto filter_op = std::make_shared<MockFilterOperator>("filter", "important");
    auto sink_op = std::make_shared<MockSinkOperator>("sink");

    auto source_id = graph->addOperator(source_op);
    auto filter_id = graph->addOperator(filter_op);
    auto sink_id = graph->addOperator(sink_op);

    graph->connectOperators(source_id, filter_id);
    graph->connectOperators(filter_id, sink_id);

    // Submit and execute
    auto graph_id = engine.submitGraph(graph);
    engine.executeGraph(graph_id);

    // Check results
    auto sink_op_ptr = std::dynamic_pointer_cast<MockSinkOperator>(
        graph->getOperator(sink_id));
    ASSERT_TRUE(sink_op_ptr != nullptr);

    const auto& received = sink_op_ptr->getReceivedMessages();
    EXPECT_EQ(received.size(), 2);
    EXPECT_EQ(received[0], "important: msg1");
    EXPECT_EQ(received[1], "important: msg3");
}

// =============================================================================
// StreamEngine 状态管理测试
// =============================================================================

TEST(StreamEngineTest, GraphStateTransitions) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);

    // Initial state should be SUBMITTED
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::SUBMITTED);

    // Execute graph
    engine.executeGraph(graph_id);

    // After execution, should be COMPLETED
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::COMPLETED);
}

TEST(StreamEngineTest, GraphControlOperations) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);

    // Execute first to change state to RUNNING
    engine.executeGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::COMPLETED);

    // Test restart and then pause
    engine.restartGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::RUNNING);

    // Test pause/resume on running graph
    engine.pauseGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::PAUSED);

    engine.resumeGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::RUNNING);

    // Test stop
    engine.stopGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::STOPPED);
}

TEST(StreamEngineTest, RestartGraph) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);

    // Execute first time
    engine.executeGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::COMPLETED);

    // Restart
    engine.restartGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::RUNNING);
}

// =============================================================================
// StreamEngine 配置测试
// =============================================================================

TEST(StreamEngineTest, ExecutionModeConfiguration) {
    StreamEngine engine;

    engine.setExecutionMode(ExecutionMode::MULTI_THREADED);
    EXPECT_EQ(engine.getExecutionMode(), ExecutionMode::MULTI_THREADED);

    engine.setExecutionMode(ExecutionMode::ASYNC);
    EXPECT_EQ(engine.getExecutionMode(), ExecutionMode::ASYNC);
}

TEST(StreamEngineTest, ExecutionStrategyConfiguration) {
    StreamEngine engine;

    engine.setExecutionStrategy(ExecutionStrategy::STREAMING);
    EXPECT_EQ(engine.getExecutionStrategy(), ExecutionStrategy::STREAMING);

    engine.setExecutionStrategy(ExecutionStrategy::BATCH);
    EXPECT_EQ(engine.getExecutionStrategy(), ExecutionStrategy::BATCH);
}

TEST(StreamEngineTest, ThreadCountConfiguration) {
    StreamEngine engine;

    engine.setThreadCount(8);
    EXPECT_EQ(engine.getThreadCount(), 8);

    engine.setThreadCount(16);
    EXPECT_EQ(engine.getThreadCount(), 16);
}

TEST(StreamEngineTest, ConfigUpdate) {
    StreamEngine engine;
    EngineConfig config;
    config.execution_mode = ExecutionMode::DISTRIBUTED;
    config.thread_pool_size = 12;
    config.execution_strategy = ExecutionStrategy::ADAPTIVE;

    engine.updateConfig(config);

    EXPECT_EQ(engine.getExecutionMode(), ExecutionMode::DISTRIBUTED);
    EXPECT_EQ(engine.getThreadCount(), 12);
    EXPECT_EQ(engine.getExecutionStrategy(), ExecutionStrategy::ADAPTIVE);
}

// =============================================================================
// StreamEngine 性能监控测试
// =============================================================================

TEST(StreamEngineTest, MetricsTracking) {
    StreamEngine engine;
    auto graph = engine.createGraph();

    auto source_op = std::make_shared<MockSourceOperator>("source",
        std::vector<std::string>{"msg1", "msg2", "msg3"});
    auto sink_op = std::make_shared<MockSinkOperator>("sink");

    auto source_id = graph->addOperator(source_op);
    auto sink_id = graph->addOperator(sink_op);
    graph->connectOperators(source_id, sink_id);

    auto graph_id = engine.submitGraph(graph);
    engine.executeGraph(graph_id);

    // Check metrics
    EXPECT_GE(engine.getTotalProcessedMessages(), 3);
    EXPECT_GE(engine.getMetrics().total_processed_messages.load(), 3);
}

TEST(StreamEngineTest, MetricsReset) {
    StreamEngine engine;

    // Execute some work first
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);
    auto graph_id = engine.submitGraph(graph);
    engine.executeGraph(graph_id);

    // Reset metrics
    engine.resetMetrics();

    EXPECT_EQ(engine.getTotalProcessedMessages(), 0);
    EXPECT_EQ(engine.getMetrics().total_processed_messages.load(), 0);
}

// =============================================================================
// StreamEngine 错误处理测试
// =============================================================================

TEST(StreamEngineTest, InvalidGraphSubmission) {
    StreamEngine engine;

    // Submit null graph - should throw exception
    EXPECT_THROW(engine.submitGraph(nullptr), std::runtime_error);
}

TEST(StreamEngineTest, ExecuteNonExistentGraph) {
    StreamEngine engine;

    // Try to execute non-existent graph - should handle gracefully without throwing
    EXPECT_NO_THROW(engine.executeGraph(999));
    // The graph state becomes ERROR for non-existent graphs
    EXPECT_EQ(engine.getGraphState(999), GraphState::ERROR);
}

TEST(StreamEngineTest, GraphStateValidation) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);

    // Execute first time
    engine.executeGraph(graph_id);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::COMPLETED);

    // Should not be able to execute again - handled gracefully
    EXPECT_NO_THROW(engine.executeGraph(graph_id));
    // State becomes ERROR when trying to execute completed graph
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::ERROR);
}

// =============================================================================
// StreamEngine 生命周期测试
// =============================================================================

TEST(StreamEngineTest, EngineLifecycle) {
    StreamEngine engine;

    // Start engine
    engine.start();
    EXPECT_TRUE(engine.isRunning());
    EXPECT_FALSE(engine.isPaused());

    // Pause engine
    engine.pause();
    EXPECT_TRUE(engine.isPaused());

    // Resume engine
    engine.resume();
    EXPECT_FALSE(engine.isPaused());

    // Stop engine
    engine.stop();
    EXPECT_FALSE(engine.isRunning());
    EXPECT_FALSE(engine.isPaused());
}

// =============================================================================
// StreamEngine 高级功能测试
// =============================================================================

TEST(StreamEngineTest, ExecuteWithCallback) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);

    bool callback_called = false;
    engine.executeWithCallback(graph_id, [&callback_called](size_t id) {
        callback_called = true;
        EXPECT_EQ(id, 0);
    });

    EXPECT_TRUE(callback_called);
}

TEST(StreamEngineTest, ExecuteGraphAsync) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);

    auto future = engine.executeGraphAsync(graph_id);
    future.wait();

    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::COMPLETED);
}

TEST(StreamEngineTest, ExecuteWithStrategy) {
    StreamEngine engine;
    auto graph = engine.createGraph();
    auto source_op = std::make_shared<MockSourceOperator>("source", std::vector<std::string>{"test"});
    graph->addOperator(source_op);

    auto graph_id = engine.submitGraph(graph);

    engine.executeGraphWithStrategy(graph_id, ExecutionStrategy::EAGER);
    EXPECT_EQ(engine.getGraphState(graph_id), GraphState::COMPLETED);
}

// =============================================================================
// 集成测试
// =============================================================================

TEST(StreamEngineIntegrationTest, ComplexGraphExecution) {
    StreamEngine engine;
    auto graph = engine.createGraph();

    // Create a more complex graph
    auto source1 = std::make_shared<MockSourceOperator>("source1",
        std::vector<std::string>{"data1", "data2"});
    auto source2 = std::make_shared<MockSourceOperator>("source2",
        std::vector<std::string>{"data3", "data4"});

    auto filter1 = std::make_shared<MockFilterOperator>("filter1", "data1");
    auto filter2 = std::make_shared<MockFilterOperator>("filter2", "data3");

    auto sink1 = std::make_shared<MockSinkOperator>("sink1");
    auto sink2 = std::make_shared<MockSinkOperator>("sink2");

    auto source1_id = graph->addOperator(source1);
    auto source2_id = graph->addOperator(source2);
    auto filter1_id = graph->addOperator(filter1);
    auto filter2_id = graph->addOperator(filter2);
    auto sink1_id = graph->addOperator(sink1);
    auto sink2_id = graph->addOperator(sink2);

    // Connect the graph
    graph->connectOperators(source1_id, filter1_id);
    graph->connectOperators(source2_id, filter2_id);
    graph->connectOperators(filter1_id, sink1_id);
    graph->connectOperators(filter2_id, sink2_id);

    // Execute
    auto graph_id = engine.submitGraph(graph);
    engine.executeGraph(graph_id);

    // Verify results
    auto sink1_ptr = std::dynamic_pointer_cast<MockSinkOperator>(
        graph->getOperator(sink1_id));
    auto sink2_ptr = std::dynamic_pointer_cast<MockSinkOperator>(
        graph->getOperator(sink2_id));

    ASSERT_TRUE(sink1_ptr != nullptr);
    ASSERT_TRUE(sink2_ptr != nullptr);

    EXPECT_EQ(sink1_ptr->getReceivedMessages().size(), 1);
    EXPECT_EQ(sink2_ptr->getReceivedMessages().size(), 1);
    EXPECT_EQ(sink1_ptr->getReceivedMessages()[0], "data1");
    EXPECT_EQ(sink2_ptr->getReceivedMessages()[0], "data3");
}

// =============================================================================
// 主函数
// =============================================================================

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}

}  // namespace sage_flow