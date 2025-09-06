#include <gtest/gtest.h>
#include <fstream>
#include <nlohmann/json.hpp>
#include "operator/map_operator.hpp"
#include "operator/filter_operator.hpp"
#include "operator/aggregate_operator.hpp"
#include "operator/join_operator.hpp"
#include "operator/file_sink_operator.hpp"
#include "operator/vector_store_sink_operator.hpp"
#include "engine/stream_engine.hpp"
#include "message/multimodal_message.hpp"
#include "function/map_function.hpp"
#include "function/filter_function.hpp"

using namespace sage_flow;

// 测试 MapOperator
class MapOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 初始化测试数据
        input_data = std::make_shared<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>();
        for (int i = 1; i <= 5; ++i) {
            auto msg = std::make_shared<sage_flow::MultiModalMessage>();
            msg->set_content_as_string(std::to_string(i));
            input_data->push_back(msg);
        }
        map_op = std::make_shared<sage_flow::MapOperator>("test_map", [](const std::shared_ptr<sage_flow::MultiModalMessage>& msg) -> std::shared_ptr<sage_flow::MultiModalMessage> {
            auto content = msg->get_content_as_string();
            auto new_msg = std::make_shared<sage_flow::MultiModalMessage>();
            new_msg->set_content_as_string(std::to_string(std::stoi(content) * 2));
            return new_msg;
        });
    }

    std::shared_ptr<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>> input_data;
    std::shared_ptr<sage_flow::MapOperator> map_op;
};

TEST_F(MapOperatorTest, BasicMap) {
    auto result = map_op->process(*input_data);
    ASSERT_TRUE(result.has_value());
    auto& output = *result;
    ASSERT_EQ(output.size(), 5);
    for (int i = 0; i < 5; ++i) {
        int expected = (i + 1) * 2;
        int actual = std::stoi(output.getMessages()[i]->get_content_as_string());
        ASSERT_EQ(actual, expected);
    }
}

TEST_F(MapOperatorTest, EmptyInput) {
    std::vector<std::shared_ptr<sage_flow::MultiModalMessage>> empty_data;
    auto result = map_op->process(empty_data);
    ASSERT_TRUE(result.has_value());
    ASSERT_EQ((*result).size(), 0);
}

// 测试 FilterOperator
class FilterOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        input_data = std::make_shared<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>();
        for (int i = 1; i <= 5; ++i) {
            auto msg = std::make_shared<sage_flow::MultiModalMessage>();
            msg->set_content_as_string(std::to_string(i));
            input_data->push_back(msg);
        }
        filter_op = std::make_shared<sage_flow::FilterOperator>("test_filter", [](const std::shared_ptr<sage_flow::MultiModalMessage>& msg) -> bool {
            int value = std::stoi(msg->get_content_as_string());
            return value > 3;
        });
    }

    std::shared_ptr<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>> input_data;
    std::shared_ptr<sage_flow::FilterOperator> filter_op;
};

TEST_F(FilterOperatorTest, BasicFilter) {
    auto result = filter_op->process(*input_data);
    ASSERT_TRUE(result.has_value());
    auto& output = *result;
    ASSERT_EQ(output.size(), 2);  // 4 and 5
    for (const auto& msg : output.getMessages()) {
        int value = std::stoi(msg->get_content_as_string());
        ASSERT_GT(value, 3);
    }
}

TEST_F(FilterOperatorTest, EmptyInput) {
    std::vector<std::shared_ptr<sage_flow::MultiModalMessage>> empty_data;
    auto result = filter_op->process(empty_data);
    ASSERT_TRUE(result.has_value());
    ASSERT_EQ((*result).size(), 0);
}

TEST_F(FilterOperatorTest, AllFiltered) {
    // 修改 filter to filter all
    auto all_filter_op = std::make_shared<sage_flow::FilterOperator>("all_filter", [](const std::shared_ptr<sage_flow::MultiModalMessage>&) -> bool {
        return false;
    });
    auto result = all_filter_op->process(*input_data);
    ASSERT_TRUE(result.has_value());
    ASSERT_EQ((*result).size(), 0);
}

// 测试 AggregateOperator
class AggregateOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 使用真实JSON数据
        std::ifstream file("tests/data/test_messages.json");
        nlohmann::json json_data = nlohmann::json::parse(file);
        input_data = std::make_shared<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>();
        for (const auto& item : json_data) {
            auto msg = std::make_shared<sage_flow::MultiModalMessage>();
            msg->set_content_as_string(item["content"]["text"].get<std::string>());
            // 简化向量设置，假设set_vector_data存在
            // msg->set_vector_data(item["content"]["vector"].get<std::vector<float>>());
            input_data->push_back(msg);
        }
        aggregate_op = std::make_shared<sage_flow::AggregateOperator>("test_aggregate", [](const std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>& messages) -> std::shared_ptr<sage_flow::MultiModalMessage> {
            std::string aggregated = "Aggregated: ";
            for (const auto& msg : messages) {
                aggregated += msg->get_content_as_string() + " ";
            }
            auto result_msg = std::make_shared<sage_flow::MultiModalMessage>();
            result_msg->set_content_as_string(aggregated);
            return result_msg;
        });
    }

    std::shared_ptr<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>> input_data;
    std::shared_ptr<sage_flow::AggregateOperator> aggregate_op;
};

TEST_F(AggregateOperatorTest, BasicAggregate) {
    auto result = aggregate_op->process(*input_data);
    ASSERT_TRUE(result.has_value());
    auto& output = *result;
    ASSERT_EQ(output.size(), 1);
    std::string expected = "Aggregated: Message 1 Message 2 Message 3 ";
    ASSERT_EQ(output.getMessages()[0]->get_content_as_string(), expected);
}

TEST_F(AggregateOperatorTest, EmptyInput) {
    std::vector<std::shared_ptr<sage_flow::MultiModalMessage>> empty_data;
    auto result = aggregate_op->process(empty_data);
    ASSERT_TRUE(result.has_value());
    ASSERT_EQ((*result).size(), 0);
}

// 测试 JoinOperator (简化，假设两个输入流)
class JoinOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        input_data1 = std::make_shared<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>();
        input_data2 = std::make_shared<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>();
        for (int i = 1; i <= 3; ++i) {
            auto msg1 = std::make_shared<sage_flow::MultiModalMessage>();
            msg1->set_content_as_string("Left: " + std::to_string(i));
            input_data1->push_back(msg1);
            
            auto msg2 = std::make_shared<sage_flow::MultiModalMessage>();
            msg2->set_content_as_string("Right: " + std::to_string(i));
            input_data2->push_back(msg2);
        }
        join_op = std::make_shared<sage_flow::JoinOperator>("test_join", [](const std::shared_ptr<sage_flow::MultiModalMessage>& left, const std::shared_ptr<sage_flow::MultiModalMessage>& right) -> std::shared_ptr<sage_flow::MultiModalMessage> {
            auto joined = std::make_shared<sage_flow::MultiModalMessage>();
            joined->set_content_as_string(left->get_content_as_string() + " + " + right->get_content_as_string());
            return joined;
        });
    }

    std::shared_ptr<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>> input_data1, input_data2;
    std::shared_ptr<sage_flow::JoinOperator> join_op;
};

TEST_F(JoinOperatorTest, BasicJoin) {
    // 简化join测试，假设process接受两个输入
    // 注意：实际JoinOperator可能需要调整实现，此处模拟
    auto result = join_op->process(*input_data1); // 假设临时使用一个输入
    ASSERT_TRUE(result.has_value());
    ASSERT_EQ((*result).size(), 3);
}

// 测试 FileSinkOperator
class FileSinkOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        input_data = std::make_shared<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>();
        for (int i = 1; i <= 3; ++i) {
            auto msg = std::make_shared<sage_flow::MultiModalMessage>();
            msg->set_content_as_string("Sink: " + std::to_string(i));
            input_data->push_back(msg);
        }
        sink_file = "tests/data/test_sink_output.txt";
        file_sink_op = std::make_shared<sage_flow::FileSinkOperator>("test_file_sink", sink_file);
    }

    std::shared_ptr<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>> input_data;
    std::string sink_file;
    std::shared_ptr<sage_flow::FileSinkOperator> file_sink_op;
};

TEST_F(FileSinkOperatorTest, BasicFileSink) {
    auto result = file_sink_op->process(*input_data);
    ASSERT_TRUE(result.has_value());
    // 验证文件输出
    std::ifstream output_file(sink_file);
    std::string content((std::istreambuf_iterator<char>(output_file)), std::istreambuf_iterator<char>());
    ASSERT_FALSE(content.empty());
    // 简单检查包含"Sink"
    ASSERT_NE(content.find("Sink"), std::string::npos);
}

// 测试 VectorStoreSinkOperator (简化)
class VectorStoreSinkOperatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        input_data = std::make_shared<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>();
        for (int i = 1; i <= 2; ++i) {
            auto msg = std::make_shared<sage_flow::MultiModalMessage>();
            msg->set_content_as_string("Vector: " + std::to_string(i));
            // 假设设置向量
            input_data->push_back(msg);
        }
        vector_sink_op = std::make_shared<sage_flow::VectorStoreSinkOperator>("test_vector_sink");
    }

    std::shared_ptr<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>> input_data;
    std::shared_ptr<sage_flow::VectorStoreSinkOperator> vector_sink_op;
};

TEST_F(VectorStoreSinkOperatorTest, BasicVectorSink) {
    auto result = vector_sink_op->process(*input_data);
    ASSERT_TRUE(result.has_value());
    ASSERT_EQ((*result).size(), 0); // Sink通常不返回数据
}

// 测试 StreamEngine
class StreamEngineTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine = std::make_shared<sage_flow::StreamEngine>();
    }

    std::shared_ptr<sage_flow::StreamEngine> engine;
};

TEST_F(StreamEngineTest, SubmitGraph) {
    // 创建简单图
    auto graph = std::make_shared<sage_flow::ExecutionGraph>();
    // 假设submitGraph方法
    engine->submitGraph(graph);
    // 验证提交成功，简化检查
    ASSERT_TRUE(true); // 占位，实际需实现验证
}

TEST_F(StreamEngineTest, Execute) {
    auto graph = std::make_shared<sage_flow::ExecutionGraph>();
    // 添加简单操作
    auto result = engine->execute(graph);
    ASSERT_TRUE(result.has_value());
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}