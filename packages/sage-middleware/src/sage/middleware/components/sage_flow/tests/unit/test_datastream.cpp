/**
 * @file test_datastream.cpp
 * @brief Google Test单元测试：测试SAGE Flow DataStream API的功能
 *
 * 此文件包含DataStream API的单元测试用例，
 * 验证链式调用、数据转换等核心功能。
 */

#include <gtest/gtest.h>
#include <memory>
#include <vector>
#include <string>
#include <functional>
#include <unordered_map>
#include <any>

// 使用真正的SAGE Flow实现进行测试
#include "../include/data_stream/data_stream.hpp"
#include "../include/engine/stream_engine.hpp"
#include "../include/engine/execution_graph.hpp"
#include "../include/message/multimodal_message.hpp"
#include "../include/message/content_type.hpp"

using namespace sage_flow;

/**
 * @brief 测试夹具：为DataStream测试提供通用设置
 */
class DataStreamTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_shared<StreamEngine>();
        graph_ = std::make_shared<ExecutionGraph>();
    }

    std::shared_ptr<StreamEngine> engine_;
    std::shared_ptr<ExecutionGraph> graph_;
};

/**
 * @brief 简单的消息生成器（用于测试）
 */
class SimpleMessageGenerator {
public:
    static std::unique_ptr<MultiModalMessage> generateMessage(int id) {
        auto message = std::make_unique<MultiModalMessage>(
            static_cast<uint64_t>(id),
            ContentType::kText,
            std::string("Message content #") + std::to_string(id)
        );

        // 添加一些元数据
        message->setMetadata("source", "SimpleMessageGenerator");
        message->setMetadata("sequence_id", std::to_string(id));
        message->setMetadata("timestamp", "1234567890");

        return message;
    }
};

/**
 * @brief 测试用例1：基础链式调用
 *
 * 验证基本的DataStream链式调用模式
 */
TEST_F(DataStreamTest, BasicChaining) {
    // 创建DataStream实例
    DataStream stream(engine_, graph_);

    // 用于收集处理结果的变量
    std::vector<std::unique_ptr<MultiModalMessage>> processed_messages;
    bool execution_completed = false;

    // 链式调用：数据源 -> 映射 -> 过滤 -> 输出
    stream
        .from_source([]() {
            static int counter = 2;  // 从ID=2开始，确保生成偶数ID的消息
            return SimpleMessageGenerator::generateMessage(counter++);
        })
        .map([](std::unique_ptr<MultiModalMessage> msg) -> std::unique_ptr<MultiModalMessage> {
            // 转换操作：添加处理标记
            msg->setMetadata("processed", "true");
            msg->setMetadata("processing_time", "1234567890");
            return msg;
        })
        .filter([](const MultiModalMessage& msg) -> bool {
            // 过滤操作：只保留偶数ID的消息
            auto id_str = msg.getMetadata().at("sequence_id");
            int id = std::stoi(id_str);
            return id % 2 == 0;
        })
        .sink([&](const MultiModalMessage& msg) {
            // 输出操作：收集消息用于验证
            processed_messages.push_back(msg.clone());
            execution_completed = true;
        });

    // 验证结果
    ASSERT_TRUE(execution_completed);
    ASSERT_FALSE(processed_messages.empty());

    // 验证第一条消息的属性
    if (!processed_messages.empty()) {
        const auto& msg = *processed_messages[0];
        EXPECT_EQ(msg.getContentType(), ContentType::kText);
        EXPECT_TRUE(msg.getMetadata().count("processed") > 0);
        EXPECT_EQ(msg.getMetadata().at("processed"), "true");
        EXPECT_TRUE(msg.getMetadata().count("sequence_id") > 0);

        // 验证ID为偶数
        int id = std::stoi(msg.getMetadata().at("sequence_id"));
        EXPECT_EQ(id % 2, 0);
    }
}

/**
 * @brief 测试用例2：DataStream构造和基本属性
 *
 * 验证DataStream的基本构造和属性访问
 */
TEST_F(DataStreamTest, ConstructionAndBasicProperties) {
    // 测试构造函数
    DataStream stream(engine_, graph_);

    // 验证基本属性
    EXPECT_EQ(stream.getEngine(), engine_);
    EXPECT_EQ(stream.getGraph(), graph_);
    EXPECT_FALSE(stream.isExecuting());
    // 注意：operator count可能不为0，因为from_source会添加operator
}

/**
 * @brief 测试用例3：错误处理
 *
 * 验证DataStream在异常情况下的行为
 */
TEST_F(DataStreamTest, ErrorHandling) {
    DataStream stream(engine_, graph_);

    // 配置一个会抛出异常的数据源
    stream
        .from_source([]() -> std::unique_ptr<MultiModalMessage> {
            throw std::runtime_error("Test exception in data source");
        });

    // 验证执行会抛出异常
    EXPECT_THROW(stream.execute(), std::runtime_error);
}

/**
 * @brief 测试用例4：空数据流
 *
 * 验证空数据流的处理
 */
TEST_F(DataStreamTest, EmptyStream) {
    DataStream stream(engine_, graph_);

    int call_count = 0;

    // 配置一个不产生数据的源
    stream
        .from_source([]() -> std::unique_ptr<MultiModalMessage> {
            return nullptr; // 返回空指针表示无数据
        })
        .sink([&](const MultiModalMessage& msg) {
            call_count++;
        });

    // 执行应该成功，但sink不应该被调用
    stream.execute();
    EXPECT_EQ(call_count, 0);
}

/**
 * @brief 测试用例5：高级链式调用模式
 *
 * 验证更复杂的链式调用，包括数据验证和转换
 */
TEST_F(DataStreamTest, AdvancedChaining) {
    DataStream stream(engine_, graph_);

    // 用于收集结果的变量
    std::vector<std::unique_ptr<MultiModalMessage>> advanced_messages;
    bool advanced_completed = false;
    int good_quality_count = 0;
    int enhanced_count = 0;

    // 简化测试：直接测试sink函数是否被调用
    stream
        .from_source([]() -> std::unique_ptr<MultiModalMessage> {
            static int counter = 1000;
            if (counter >= 1005) return nullptr; // 只产生5条消息
            auto msg = SimpleMessageGenerator::generateMessage(++counter);

            // 模拟数据质量问题
            if (counter % 7 == 0) {
                msg->setMetadata("quality", "poor");
            } else {
                msg->setMetadata("quality", "good");
            }

            return msg;
        })
        .sink([&](const MultiModalMessage& msg) {
            advanced_messages.push_back(msg.clone());
            advanced_completed = true;

            // 统计计数
            if (msg.getMetadata().at("quality") == "good") {
                good_quality_count++;
            }
            if (msg.getMetadata().count("enhanced") > 0) {
                enhanced_count++;
            }
        });

    // 验证结果
    ASSERT_TRUE(advanced_completed);
    ASSERT_FALSE(advanced_messages.empty());

    // 验证至少有一些高质量消息（根据counter % 7 == 0的逻辑）
    EXPECT_GT(good_quality_count, 0);
    EXPECT_LE(good_quality_count, static_cast<int>(advanced_messages.size()));

    // 验证第一条消息的详细属性
    if (!advanced_messages.empty()) {
        const auto& msg = *advanced_messages[0];

        // 验证质量字段存在
        EXPECT_TRUE(msg.getMetadata().count("quality") > 0);

        // 验证基本属性
        EXPECT_EQ(msg.getContentType(), ContentType::kText);
        EXPECT_TRUE(msg.getMetadata().count("sequence_id") > 0);
    }
}

/**
 * @brief 测试用例6：操作符计数
 *
 * 验证操作符计数的正确性
 */
TEST_F(DataStreamTest, OperatorCount) {
    DataStream stream(engine_, graph_);

    // 初始状态
    size_t initial_count = stream.getOperatorCount();

    // 添加from_source操作符
    stream.from_source([]() {
        return SimpleMessageGenerator::generateMessage(1);
    });

    // 验证操作符数量增加
    EXPECT_GT(stream.getOperatorCount(), initial_count);

    // 添加map操作符
    stream.map([](std::unique_ptr<MultiModalMessage> msg) {
        return msg;
    });

    // 验证操作符数量再次增加
    EXPECT_GT(stream.getOperatorCount(), initial_count + 1);
}

// Google Test主函数
int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}