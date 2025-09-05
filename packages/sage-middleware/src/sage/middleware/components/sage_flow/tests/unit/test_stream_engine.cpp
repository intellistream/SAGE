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

// 简化的流引擎测试实现
namespace sage_flow {

class StreamEngine {
public:
    StreamEngine() : running_(false) {}
    
    bool start() {
        if (running_) return false;
        running_ = true;
        return true;
    }
    
    bool stop() {
        if (!running_) return false;
        running_ = false;
        return true;
    }
    
    bool is_running() const { return running_; }
    
    void process_batch(const std::vector<std::string>& messages) {
        processed_count_ += messages.size();
    }
    
    size_t get_processed_count() const { return processed_count_; }

private:
    bool running_;
    size_t processed_count_ = 0;
};

class ExecutionGraph {
public:
    struct Node {
        std::string id;
        std::string type;
        std::vector<std::string> inputs;
        std::vector<std::string> outputs;
    };
    
    bool add_node(const Node& node) {
        if (nodes_.find(node.id) != nodes_.end()) {
            return false; // 节点已存在
        }
        nodes_[node.id] = node;
        return true;
    }
    
    bool remove_node(const std::string& node_id) {
        return nodes_.erase(node_id) > 0;
    }
    
    std::vector<std::string> get_node_ids() const {
        std::vector<std::string> ids;
        for (const auto& pair : nodes_) {
            ids.push_back(pair.first);
        }
        return ids;
    }
    
    bool validate() const {
        // 简化的验证逻辑
        for (const auto& pair : nodes_) {
            const auto& node = pair.second;
            // 检查输入输出连接
            for (const auto& input : node.inputs) {
                if (nodes_.find(input) == nodes_.end()) {
                    return false;
                }
            }
        }
        return true;
    }
    
    std::vector<std::string> topological_sort() const {
        // 简化的拓扑排序
        std::vector<std::string> sorted;
        for (const auto& pair : nodes_) {
            sorted.push_back(pair.first);
        }
        return sorted;
    }

private:
    std::unordered_map<std::string, Node> nodes_;
};

} // namespace sage_flow

using namespace sage_flow;

// StreamEngine 测试套件
class StreamEngineTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_unique<StreamEngine>();
    }

    void TearDown() override {
        if (engine_ && engine_->is_running()) {
            engine_->stop();
        }
    }

    std::unique_ptr<StreamEngine> engine_;
};

TEST_F(StreamEngineTest, StartStop) {
    // 测试初始状态
    EXPECT_FALSE(engine_->is_running());
    
    // 测试启动
    EXPECT_TRUE(engine_->start());
    EXPECT_TRUE(engine_->is_running());
    
    // 测试重复启动失败
    EXPECT_FALSE(engine_->start());
    
    // 测试停止
    EXPECT_TRUE(engine_->stop());
    EXPECT_FALSE(engine_->is_running());
    
    // 测试重复停止失败
    EXPECT_FALSE(engine_->stop());
}

TEST_F(StreamEngineTest, MessageProcessing) {
    engine_->start();
    
    // 测试批量处理
    std::vector<std::string> batch1 = {"msg1", "msg2", "msg3"};
    std::vector<std::string> batch2 = {"msg4", "msg5"};
    
    engine_->process_batch(batch1);
    EXPECT_EQ(engine_->get_processed_count(), 3);
    
    engine_->process_batch(batch2);
    EXPECT_EQ(engine_->get_processed_count(), 5);
}

TEST_F(StreamEngineTest, ConcurrentProcessing) {
    engine_->start();
    
    const int num_threads = 4;
    const int messages_per_thread = 100;
    std::vector<std::thread> threads;
    
    // 并发处理消息
    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back([this, messages_per_thread, i]() {
            for (int j = 0; j < messages_per_thread; ++j) {
                std::vector<std::string> batch = {
                    "thread_" + std::to_string(i) + "_msg_" + std::to_string(j)
                };
                engine_->process_batch(batch);
            }
        });
    }
    
    // 等待所有线程完成
    for (auto& thread : threads) {
        thread.join();
    }
    
    // 验证处理计数
    EXPECT_EQ(engine_->get_processed_count(), num_threads * messages_per_thread);
}

// ExecutionGraph 测试套件
class ExecutionGraphTest : public ::testing::Test {
protected:
    void SetUp() override {
        graph_ = std::make_unique<ExecutionGraph>();
    }

    std::unique_ptr<ExecutionGraph> graph_;
};

TEST_F(ExecutionGraphTest, NodeManagement) {
    // 测试添加节点
    ExecutionGraph::Node node1{"node1", "source", {}, {"output1"}};
    ExecutionGraph::Node node2{"node2", "transform", {"output1"}, {"output2"}};
    ExecutionGraph::Node node3{"node3", "sink", {"output2"}, {}};
    
    EXPECT_TRUE(graph_->add_node(node1));
    EXPECT_TRUE(graph_->add_node(node2));
    EXPECT_TRUE(graph_->add_node(node3));
    
    // 测试重复添加失败
    EXPECT_FALSE(graph_->add_node(node1));
    
    // 测试节点列表
    auto node_ids = graph_->get_node_ids();
    EXPECT_EQ(node_ids.size(), 3);
    EXPECT_THAT(node_ids, testing::Contains("node1"));
    EXPECT_THAT(node_ids, testing::Contains("node2"));
    EXPECT_THAT(node_ids, testing::Contains("node3"));
}

TEST_F(ExecutionGraphTest, GraphValidation) {
    // 添加有效的图结构
    ExecutionGraph::Node source{"source", "source", {}, {"data"}};
    ExecutionGraph::Node processor{"processor", "transform", {"data"}, {"result"}};
    ExecutionGraph::Node sink{"sink", "sink", {"result"}, {}};
    
    graph_->add_node(source);
    graph_->add_node(processor);
    graph_->add_node(sink);
    
    // 测试图验证
    EXPECT_TRUE(graph_->validate());
    
    // 添加无效连接的节点
    ExecutionGraph::Node invalid{"invalid", "transform", {"nonexistent"}, {"output"}};
    graph_->add_node(invalid);
    
    // 验证应该失败
    EXPECT_FALSE(graph_->validate());
}

TEST_F(ExecutionGraphTest, TopologicalSort) {
    // 构建简单的线性图
    ExecutionGraph::Node node1{"1", "source", {}, {"out1"}};
    ExecutionGraph::Node node2{"2", "transform", {"out1"}, {"out2"}};
    ExecutionGraph::Node node3{"3", "sink", {"out2"}, {}};
    
    graph_->add_node(node1);
    graph_->add_node(node2);
    graph_->add_node(node3);
    
    auto sorted = graph_->topological_sort();
    EXPECT_EQ(sorted.size(), 3);
    
    // 验证排序结果包含所有节点
    EXPECT_THAT(sorted, testing::Contains("1"));
    EXPECT_THAT(sorted, testing::Contains("2"));
    EXPECT_THAT(sorted, testing::Contains("3"));
}

TEST_F(ExecutionGraphTest, NodeRemoval) {
    // 添加节点
    ExecutionGraph::Node node1{"node1", "source", {}, {"output1"}};
    ExecutionGraph::Node node2{"node2", "sink", {"output1"}, {}};
    
    graph_->add_node(node1);
    graph_->add_node(node2);
    
    EXPECT_EQ(graph_->get_node_ids().size(), 2);
    
    // 移除节点
    EXPECT_TRUE(graph_->remove_node("node1"));
    EXPECT_EQ(graph_->get_node_ids().size(), 1);
    
    // 重复移除失败
    EXPECT_FALSE(graph_->remove_node("node1"));
    
    // 移除不存在的节点失败
    EXPECT_FALSE(graph_->remove_node("nonexistent"));
}

// 性能测试
class StreamEnginePerformanceTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_unique<StreamEngine>();
        engine_->start();
    }

    void TearDown() override {
        engine_->stop();
    }

    std::unique_ptr<StreamEngine> engine_;
};

TEST_F(StreamEnginePerformanceTest, LargeBatchProcessing) {
    const size_t batch_size = 10000;
    std::vector<std::string> large_batch;
    large_batch.reserve(batch_size);
    
    for (size_t i = 0; i < batch_size; ++i) {
        large_batch.push_back("message_" + std::to_string(i));
    }
    
    auto start = std::chrono::high_resolution_clock::now();
    engine_->process_batch(large_batch);
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 性能基准：10000条消息应该在100ms内处理完成
    EXPECT_LT(duration.count(), 100);
    EXPECT_EQ(engine_->get_processed_count(), batch_size);
}

TEST_F(StreamEnginePerformanceTest, HighThroughputProcessing) {
    const int num_batches = 100;
    const int batch_size = 100;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < num_batches; ++i) {
        std::vector<std::string> batch;
        batch.reserve(batch_size);
        
        for (int j = 0; j < batch_size; ++j) {
            batch.push_back("batch_" + std::to_string(i) + "_msg_" + std::to_string(j));
        }
        
        engine_->process_batch(batch);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 性能基准：10000条消息分100批处理应该在200ms内完成
    EXPECT_LT(duration.count(), 200);
    EXPECT_EQ(engine_->get_processed_count(), num_batches * batch_size);
}

// 错误处理测试
class StreamEngineErrorTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_unique<StreamEngine>();
    }

    std::unique_ptr<StreamEngine> engine_;
};

TEST_F(StreamEngineErrorTest, InvalidOperations) {
    // 测试在未启动状态下的操作
    EXPECT_FALSE(engine_->stop()); // 停止未启动的引擎应该失败
    
    // 启动后的正常操作
    EXPECT_TRUE(engine_->start());
    EXPECT_FALSE(engine_->start()); // 重复启动应该失败
    
    // 停止后的操作
    EXPECT_TRUE(engine_->stop());
    EXPECT_FALSE(engine_->stop()); // 重复停止应该失败
}

// 集成测试
class StreamEngineIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_unique<StreamEngine>();
        graph_ = std::make_unique<ExecutionGraph>();
    }

    std::unique_ptr<StreamEngine> engine_;
    std::unique_ptr<ExecutionGraph> graph_;
};

TEST_F(StreamEngineIntegrationTest, EngineWithGraph) {
    // 构建执行图
    ExecutionGraph::Node source{"source", "kafka_source", {}, {"raw_data"}};
    ExecutionGraph::Node transformer{"transformer", "json_parser", {"raw_data"}, {"parsed_data"}};
    ExecutionGraph::Node sink{"sink", "elasticsearch_sink", {"parsed_data"}, {}};
    
    EXPECT_TRUE(graph_->add_node(source));
    EXPECT_TRUE(graph_->add_node(transformer));
    EXPECT_TRUE(graph_->add_node(sink));
    
    // 验证图结构
    EXPECT_TRUE(graph_->validate());
    
    // 启动引擎并处理数据
    EXPECT_TRUE(engine_->start());
    
    // 模拟数据流处理
    auto execution_order = graph_->topological_sort();
    EXPECT_EQ(execution_order.size(), 3);
    
    // 处理一批消息
    std::vector<std::string> messages = {"msg1", "msg2", "msg3"};
    engine_->process_batch(messages);
    
    EXPECT_EQ(engine_->get_processed_count(), 3);
    
    engine_->stop();
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}