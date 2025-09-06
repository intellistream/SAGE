#include <gtest/gtest.h>
#include <memory>
#include <vector>
#include <string>
#include <iostream>

// 使用真正的SAGE Flow实现进行测试
#include "../include/data_stream/data_stream.hpp"
#include "../include/engine/stream_engine.hpp"
#include "../include/engine/execution_graph.hpp"
#include "../include/message/multimodal_message.hpp"
#include "../include/message/content_type.hpp"

using namespace sage_flow;

/**
 * @brief 测试collect()方法的C++单元测试
 */
class CollectTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_shared<StreamEngine>();
        graph_ = std::make_shared<ExecutionGraph>();
    }

    void TearDown() override {
        if (engine_) {
            engine_.reset();
        }
        if (graph_) {
            graph_.reset();
        }
    }

    std::shared_ptr<StreamEngine> engine_;
    std::shared_ptr<ExecutionGraph> graph_;
};

/**
 * @brief 测试用例：基础collect()方法
 */
TEST_F(CollectTest, BasicCollect) {
    std::cout << "=== 开始BasicCollect测试 ===" << std::endl;

    // 创建DataStream实例
    DataStream stream(engine_, graph_);

    // 用于收集结果的变量
    std::vector<std::unique_ptr<MultiModalMessage>> collected_messages;
    bool collect_called = false;

    // 配置数据流
    stream
        .from_source([]() -> std::unique_ptr<MultiModalMessage> {
            static int counter = 1;
            if (counter > 3) return nullptr; // 只产生3条消息
            auto msg = std::make_unique<MultiModalMessage>(
                static_cast<uint64_t>(counter),
                ContentType::kText,
                std::string("Test message #") + std::to_string(counter)
            );
            counter++;
            return msg;
        });

    std::cout << "调用collect()方法..." << std::endl;

    // 调用collect方法
    try {
        auto results = stream.collect();
        std::cout << "collect()成功，返回 " << results.size() << " 条消息" << std::endl;

        // 验证结果
        ASSERT_EQ(results.size(), 3);
        for (size_t i = 0; i < results.size(); ++i) {
            ASSERT_TRUE(results[i] != nullptr);
            EXPECT_EQ(results[i]->getContentType(), ContentType::kText);
            std::string content = std::get<std::string>(results[i]->getContent());
            EXPECT_TRUE(content.find("Test message") != std::string::npos);
        }

    } catch (const std::exception& e) {
        std::cout << "collect()失败: " << e.what() << std::endl;
        FAIL() << "collect()抛出异常: " << e.what();
    } catch (...) {
        std::cout << "collect()发生未知错误" << std::endl;
        FAIL() << "collect()发生未知错误";
    }
}

/**
 * @brief 测试用例：空流collect()
 */
TEST_F(CollectTest, EmptyStreamCollect) {
    std::cout << "=== 开始EmptyStreamCollect测试 ===" << std::endl;

    // 创建DataStream实例
    DataStream stream(engine_, graph_);

    // 配置空数据源
    stream
        .from_source([]() -> std::unique_ptr<MultiModalMessage> {
            return nullptr; // 不产生任何消息
        });

    std::cout << "调用collect()方法..." << std::endl;

    // 调用collect方法
    try {
        auto results = stream.collect();
        std::cout << "collect()成功，返回 " << results.size() << " 条消息" << std::endl;

        // 验证结果
        EXPECT_EQ(results.size(), 0);

    } catch (const std::exception& e) {
        std::cout << "collect()失败: " << e.what() << std::endl;
        FAIL() << "collect()抛出异常: " << e.what();
    } catch (...) {
        std::cout << "collect()发生未知错误" << std::endl;
        FAIL() << "collect()发生未知错误";
    }
}

/**
 * @brief 测试用例：from_list + collect()
 */
TEST_F(CollectTest, FromListCollect) {
    std::cout << "=== 开始FromListCollect测试 ===" << std::endl;

    // 创建测试数据
    std::vector<std::unordered_map<std::string, std::variant<std::string, int64_t, double, bool>>> test_data = {
        {{"id", std::string("1")}, {"name", std::string("Alice")}, {"age", int64_t(25)}},
        {{"id", std::string("2")}, {"name", std::string("Bob")}, {"age", int64_t(30)}}
    };

    std::cout << "使用from_list创建流..." << std::endl;

    // 使用from_list创建DataStream
    auto stream = DataStream::from_list(test_data, engine_);

    std::cout << "调用collect()方法..." << std::endl;

    // 调用collect方法
    try {
        auto results = stream.collect();
        std::cout << "collect()成功，返回 " << results.size() << " 条消息" << std::endl;

        // 验证结果
        ASSERT_EQ(results.size(), test_data.size());
        for (size_t i = 0; i < results.size(); ++i) {
            ASSERT_TRUE(results[i] != nullptr);
            EXPECT_EQ(results[i]->getContentType(), ContentType::kText);

            // 检查内容包含JSON数据
            std::string content = std::get<std::string>(results[i]->getContent());
            EXPECT_TRUE(content.find("\"id\":") != std::string::npos);
            EXPECT_TRUE(content.find("\"name\":") != std::string::npos);
        }

    } catch (const std::exception& e) {
        std::cout << "collect()失败: " << e.what() << std::endl;
        FAIL() << "collect()抛出异常: " << e.what();
    } catch (...) {
        std::cout << "collect()发生未知错误" << std::endl;
        FAIL() << "collect()发生未知错误";
    }
}

// Google Test主函数
int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}