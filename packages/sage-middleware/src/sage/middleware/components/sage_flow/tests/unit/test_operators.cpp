/**
 * @file test_operators.cpp
 * @brief 操作符单元测试
 *
 * 测试 Map, Filter, Aggregate, Source, Sink 等核心操作符
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <memory>
#include <vector>
#include <string>
#include <functional>
#include <algorithm>
#include <chrono>

// Operator headers
#include "../../include/operator/base_operator.hpp"
#include "../../include/operator/map_operator.hpp"
#include "../../include/operator/filter_operator.hpp"
#include "../../include/operator/source_operator.hpp"
#include "../../include/operator/sink_operator.hpp"

// Function headers
#include "../../include/function/map_function.hpp"
#include "../../include/function/filter_function.hpp"
#include "../../include/function/sink_function.hpp"

// Message and response headers
#include "../../include/message/multimodal_message.hpp"
#include "../../include/message/content_type.hpp"
#include "../../include/operator/response.hpp"
#include "../../include/function/function_response.hpp"

// Operator types
#include "../../include/operator/operator_types.hpp"

// Mock classes for testing
class MockSinkFunction : public sage_flow::SinkFunction {
public:
    explicit MockSinkFunction(const std::string& name)
        : sage_flow::SinkFunction(name) {}

    void init() override {}
    void close() override {}

    // Note: Mocking virtual functions with different signatures requires special handling
    // For this test, we'll use a simple implementation
    sage_flow::FunctionResponse execute(sage_flow::FunctionResponse& response) override {
        mockExecute(response);
        return sage_flow::FunctionResponse{};
    }

    MOCK_METHOD(void, mockExecute, (sage_flow::FunctionResponse& response), ());
};

class TestSourceOperator : public sage_flow::SourceOperator {
public:
    explicit TestSourceOperator(std::string name)
        : sage_flow::SourceOperator(std::move(name)) {}

    auto hasNext() -> bool override {
        return message_count_ < 3; // Generate 3 messages
    }

    auto next() -> std::unique_ptr<sage_flow::MultiModalMessage> override {
        if (message_count_ >= 3) return nullptr;

        auto message = std::make_unique<sage_flow::MultiModalMessage>(
            static_cast<uint64_t>(message_count_ + 1),
            sage_flow::ContentType::kText,
            std::string("Test message ") + std::to_string(message_count_ + 1)
        );
        message_count_++;
        return message;
    }

    auto reset() -> void override {
        message_count_ = 0;
    }

private:
    int message_count_ = 0;
};

// Test fixtures
class OperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create test messages
        test_message1_ = std::make_unique<sage_flow::MultiModalMessage>(
            1, sage_flow::ContentType::kText, std::string("Hello World")
        );
        test_message2_ = std::make_unique<sage_flow::MultiModalMessage>(
            2, sage_flow::ContentType::kText, std::string("Test Message")
        );
    }

    std::unique_ptr<sage_flow::MultiModalMessage> test_message1_;
    std::unique_ptr<sage_flow::MultiModalMessage> test_message2_;
};

// BaseOperator functionality is tested through derived classes

// MapOperator Tests
TEST_F(OperatorTest, MapOperatorConstruction) {
    sage_flow::MapOperator op("test_map");
    EXPECT_EQ(op.getType(), sage_flow::OperatorType::kMap);
    EXPECT_EQ(op.getName(), "test_map");
}

TEST_F(OperatorTest, MapOperatorWithFunction) {
    auto map_func = std::make_unique<sage_flow::MapFunction>("test_map_func");
    map_func->setMapFunc([](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        if (msg) {
            std::string content = msg->getContentAsString();
            msg->setContent(content + " mapped");
        }
    });

    sage_flow::MapOperator op("test_map", std::move(map_func));

    // Create input response
    sage_flow::Response input_response(test_message1_->clone());
    bool result = op.process(input_response, 0);

    EXPECT_TRUE(result);
    EXPECT_EQ(op.getProcessedCount(), 1u);
    EXPECT_EQ(op.getOutputCount(), 1u);
}

TEST_F(OperatorTest, MapOperatorWithoutFunction) {
    sage_flow::MapOperator op("test_map");

    sage_flow::Response input_response(test_message1_->clone());
    EXPECT_THROW(op.process(input_response, 0), std::runtime_error);
}

TEST_F(OperatorTest, MapOperatorEmptyInput) {
    auto map_func = std::make_unique<sage_flow::MapFunction>("test_map_func");
    map_func->setMapFunc([](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        if (msg) {
            std::string content = msg->getContentAsString();
            msg->setContent(content + " mapped");
        }
    });

    sage_flow::MapOperator op("test_map", std::move(map_func));

    sage_flow::Response empty_response(std::vector<std::unique_ptr<sage_flow::MultiModalMessage>>{});
    bool result = op.process(empty_response, 0);

    EXPECT_FALSE(result);
    EXPECT_EQ(op.getProcessedCount(), 0u);
}

// FilterOperator Tests
TEST_F(OperatorTest, FilterOperatorConstruction) {
    sage_flow::FilterOperator op("test_filter");
    EXPECT_EQ(op.getType(), sage_flow::OperatorType::kFilter);
    EXPECT_EQ(op.getName(), "test_filter");
}

TEST_F(OperatorTest, FilterOperatorWithFunction) {
    auto filter_func = std::make_unique<sage_flow::FilterFunction>("test_filter_func");
    filter_func->setFilterFunc([](const sage_flow::MultiModalMessage& msg) {
        return msg.getContentAsString().find("Hello") != std::string::npos;
    });

    sage_flow::FilterOperator op("test_filter", std::move(filter_func));

    // Test message that passes filter
    sage_flow::Response input_response1(test_message1_->clone()); // "Hello World"
    bool result1 = op.process(input_response1, 0);
    EXPECT_TRUE(result1);

    // Test message that doesn't pass filter
    sage_flow::Response input_response2(test_message2_->clone()); // "Test Message"
    bool result2 = op.process(input_response2, 0);
    EXPECT_FALSE(result2);

    EXPECT_EQ(op.getProcessedCount(), 2u);
}

TEST_F(OperatorTest, FilterOperatorWithoutFunction) {
    sage_flow::FilterOperator op("test_filter");

    sage_flow::Response input_response(test_message1_->clone());
    EXPECT_THROW(op.process(input_response, 0), std::runtime_error);
}

TEST_F(OperatorTest, FilterOperatorEmptyInput) {
    auto filter_func = std::make_unique<sage_flow::FilterFunction>("test_filter_func");
    filter_func->setFilterFunc([](const sage_flow::MultiModalMessage& msg) {
        return true; // Accept all
    });

    sage_flow::FilterOperator op("test_filter", std::move(filter_func));

    sage_flow::Response empty_response(std::vector<std::unique_ptr<sage_flow::MultiModalMessage>>{});
    bool result = op.process(empty_response, 0);

    EXPECT_FALSE(result);
    EXPECT_EQ(op.getProcessedCount(), 0u);
}

// SourceOperator Tests
TEST_F(OperatorTest, SourceOperatorConstruction) {
    TestSourceOperator op("test_source");
    EXPECT_EQ(op.getType(), sage_flow::OperatorType::kSource);
    EXPECT_EQ(op.getName(), "test_source");
}

TEST_F(OperatorTest, SourceOperatorHasNext) {
    TestSourceOperator op("test_source");

    // Initially should have next
    EXPECT_TRUE(op.hasNext());

    // Generate messages
    for (int i = 0; i < 3; ++i) {
        EXPECT_TRUE(op.hasNext());
        auto msg = op.next();
        ASSERT_TRUE(msg);
    }

    // Should not have next after 3 messages
    EXPECT_FALSE(op.hasNext());
}

TEST_F(OperatorTest, SourceOperatorNext) {
    TestSourceOperator op("test_source");

    for (int i = 0; i < 3; ++i) {
        auto msg = op.next();
        ASSERT_TRUE(msg);
        EXPECT_EQ(msg->getContentAsString(), "Test message " + std::to_string(i + 1));
    }

    // Should return nullptr after 3 messages
    auto null_msg = op.next();
    EXPECT_FALSE(null_msg);
}

TEST_F(OperatorTest, SourceOperatorReset) {
    TestSourceOperator op("test_source");

    // Generate some messages
    op.next();
    op.next();

    // Reset
    op.reset();

    // Should start from beginning again
    auto msg = op.next();
    ASSERT_TRUE(msg);
    EXPECT_EQ(msg->getContentAsString(), "Test message 1");
}

TEST_F(OperatorTest, SourceOperatorProcess) {
    TestSourceOperator op("test_source");

    sage_flow::Response dummy_input(std::vector<std::unique_ptr<sage_flow::MultiModalMessage>>{});
    bool result = op.process(dummy_input, 0);

    EXPECT_TRUE(result);
    EXPECT_EQ(op.getProcessedCount(), 1u);
    EXPECT_EQ(op.getOutputCount(), 1u);
}

// SinkOperator Tests
TEST_F(OperatorTest, SinkOperatorConstruction) {
    sage_flow::SinkOperator op("test_sink");
    EXPECT_EQ(op.getType(), sage_flow::OperatorType::kSink);
    EXPECT_EQ(op.getName(), "test_sink");
}

TEST_F(OperatorTest, SinkOperatorWithFunction) {
    auto sink_func = std::make_unique<MockSinkFunction>("test_sink_func");
    EXPECT_CALL(*sink_func, mockExecute(::testing::_))
        .Times(1);

    sage_flow::SinkOperator op("test_sink", std::move(sink_func));

    sage_flow::Response input_response(test_message1_->clone());
    bool result = op.process(input_response, 0);

    EXPECT_TRUE(result);
    EXPECT_EQ(op.getProcessedCount(), 1u);
    EXPECT_EQ(op.getOutputCount(), 0u); // Sinks don't produce output
}

TEST_F(OperatorTest, SinkOperatorWithoutFunction) {
    sage_flow::SinkOperator op("test_sink");

    sage_flow::Response input_response(test_message1_->clone());
    EXPECT_THROW(op.process(input_response, 0), std::runtime_error);
}

TEST_F(OperatorTest, SinkOperatorEmptyInput) {
    auto sink_func = std::make_unique<MockSinkFunction>("test_sink_func");
    EXPECT_CALL(*sink_func, mockExecute(::testing::_))
        .Times(0); // Should not be called for empty input

    sage_flow::SinkOperator op("test_sink", std::move(sink_func));

    sage_flow::Response empty_response(std::vector<std::unique_ptr<sage_flow::MultiModalMessage>>{});
    bool result = op.process(empty_response, 0);

    EXPECT_FALSE(result);
    EXPECT_EQ(op.getProcessedCount(), 0u);
}

TEST_F(OperatorTest, SinkOperatorFlush) {
    auto sink_func = std::make_unique<MockSinkFunction>("test_sink_func");
    sage_flow::SinkOperator op("test_sink", std::move(sink_func));

    // Flush should not throw
    EXPECT_NO_THROW(op.flush());
}

// Integration Tests
TEST_F(OperatorTest, OperatorChain) {
    // Create a simple processing chain: Source -> Map -> Filter -> Sink

    // Source
    TestSourceOperator source("source");

    // Map function
    auto map_func = std::make_unique<sage_flow::MapFunction>("map_func");
    map_func->setMapFunc([](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        if (msg) {
            std::string content = msg->getContentAsString();
            msg->setContent(content + " processed");
            std::cout << "[TEST] MapOperator processed message: " << content << " -> " << msg->getContentAsString() << std::endl;
        }
    });
    sage_flow::MapOperator mapper("mapper", std::move(map_func));

    // Filter function
    auto filter_func = std::make_unique<sage_flow::FilterFunction>("filter_func");
    filter_func->setFilterFunc([](const sage_flow::MultiModalMessage& msg) {
        bool result = msg.getContentAsString().find("processed") != std::string::npos;
        std::cout << "[TEST] FilterOperator checking message: " << msg.getContentAsString() << " -> " << (result ? "PASS" : "FAIL") << std::endl;
        return result;
    });
    sage_flow::FilterOperator filter("filter", std::move(filter_func));

    // Sink
    auto sink_func = std::make_unique<MockSinkFunction>("sink_func");
    EXPECT_CALL(*sink_func, mockExecute(::testing::_))
        .Times(3); // All messages should pass through
    sage_flow::SinkOperator sink("sink", std::move(sink_func));

    // Add logging to check emit callbacks
    std::cout << "[TEST] Source emit callback set: " << (source.getEmitCallback() ? "YES" : "NO") << std::endl;
    std::cout << "[TEST] Mapper emit callback set: " << (mapper.getEmitCallback() ? "YES" : "NO") << std::endl;
    std::cout << "[TEST] Filter emit callback set: " << (filter.getEmitCallback() ? "YES" : "NO") << std::endl;
    std::cout << "[TEST] Sink emit callback set: " << (sink.getEmitCallback() ? "YES" : "NO") << std::endl;

    // Connect operators with proper message passing through emit callbacks
    // Source -> Map -> Filter -> Sink

    // Connect Source to Map
    source.setEmitCallback([&mapper](int output_id, sage_flow::Response& response) {
        std::cout << "[TEST] Source emitting to Mapper" << std::endl;
        mapper.process(response, 0);
    });

    // Connect Map to Filter
    mapper.setEmitCallback([&filter](int output_id, sage_flow::Response& response) {
        std::cout << "[TEST] Mapper emitting to Filter" << std::endl;
        filter.process(response, 0);
    });

    // Connect Filter to Sink
    filter.setEmitCallback([&sink](int output_id, sage_flow::Response& response) {
        std::cout << "[TEST] Filter emitting to Sink" << std::endl;
        sink.process(response, 0);
    });

    // Process messages through the chain - only call source, messages will flow through the chain
    for (int i = 0; i < 3; ++i) {
        sage_flow::Response dummy(std::vector<std::unique_ptr<sage_flow::MultiModalMessage>>{});
        bool source_result = source.process(dummy, 0);
        EXPECT_TRUE(source_result);
        std::cout << "[TEST] Processed message " << i << " through chain" << std::endl;
    }

    // Verify all operators processed the messages
    EXPECT_EQ(source.getProcessedCount(), 3u);
    EXPECT_EQ(source.getOutputCount(), 3u);
    EXPECT_EQ(mapper.getProcessedCount(), 3u);
    EXPECT_EQ(mapper.getOutputCount(), 3u);
    EXPECT_EQ(filter.getProcessedCount(), 3u);
    EXPECT_EQ(filter.getOutputCount(), 3u);
    EXPECT_EQ(sink.getProcessedCount(), 3u);
    EXPECT_EQ(sink.getOutputCount(), 0u); // Sink doesn't produce output

    std::cout << "[TEST] Final counts - Source processed: " << source.getProcessedCount()
              << ", output: " << source.getOutputCount() << std::endl;
    std::cout << "[TEST] Final counts - Mapper processed: " << mapper.getProcessedCount()
              << ", output: " << mapper.getOutputCount() << std::endl;
    std::cout << "[TEST] Final counts - Filter processed: " << filter.getProcessedCount()
              << ", output: " << filter.getOutputCount() << std::endl;
    std::cout << "[TEST] Final counts - Sink processed: " << sink.getProcessedCount()
              << ", output: " << sink.getOutputCount() << std::endl;
}

// Performance Tests
TEST_F(OperatorTest, OperatorPerformance) {
    auto map_func = std::make_unique<sage_flow::MapFunction>("perf_map_func");
    map_func->setMapFunc([](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        if (msg) {
            msg->addProcessingStep("performance_test");
        }
    });

    sage_flow::MapOperator op("perf_test", std::move(map_func));

    const int num_iterations = 1000;
    auto start_time = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < num_iterations; ++i) {
        auto msg = std::make_unique<sage_flow::MultiModalMessage>(
            static_cast<uint64_t>(i), sage_flow::ContentType::kText, std::string("perf_test")
        );
        sage_flow::Response response(std::move(msg));
        op.process(response, 0);
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);

    EXPECT_EQ(op.getProcessedCount(), static_cast<uint64_t>(num_iterations));
    EXPECT_EQ(op.getOutputCount(), static_cast<uint64_t>(num_iterations));

    // Performance should be reasonable (less than 1 second for 1000 operations)
    EXPECT_LT(duration.count(), 1000);
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}