/**
 * @file test_functions.cpp
 * @brief 函数系统单元测试
 *
 * 测试各种函数组件：BaseFunction、MapFunction、FilterFunction、SinkFunction
 */

#include <gtest/gtest.h>
#include <memory>
#include <vector>
#include <string>
#include <functional>

#include "function/base_function.hpp"
#include "function/map_function.hpp"
#include "function/filter_function.hpp"
#include "function/sink_function.hpp"
#include "function/function_response.hpp"
#include "function/function_type.hpp"
#include "message/multimodal_message.hpp"
#include "message/content_type.hpp"

namespace sage_flow {

// 测试用的具体SinkFunction实现
class TestSinkFunction : public SinkFunction {
public:
    explicit TestSinkFunction(const std::string& name)
        : SinkFunction(name) {}

    TestSinkFunction(const std::string& name, sage_flow::SinkFunc sink_func)
        : SinkFunction(name, sink_func) {}

    void init() override {
        initialized_ = true;
    }

    void close() override {
        closed_ = true;
    }

    // 用于测试的数据收集
    std::vector<std::string> processed_messages;
    bool initialized_ = false;
    bool closed_ = false;
};

// 辅助函数：创建测试消息
std::unique_ptr<MultiModalMessage> createTestMessage(uint64_t uid, const std::string& content) {
    return std::make_unique<MultiModalMessage>(uid, ContentType::kText, content);
}

// 辅助函数：创建测试响应
FunctionResponse createTestResponse(const std::vector<std::string>& contents) {
    FunctionResponse response;
    for (size_t i = 0; i < contents.size(); ++i) {
        response.addMessage(createTestMessage(i + 1, contents[i]));
    }
    return response;
}

}  // namespace sage_flow

// BaseFunction测试
TEST(BaseFunctionTest, Constructor) {
    sage_flow::BaseFunction func("test_func", sage_flow::FunctionType::Map);
    EXPECT_EQ(func.getName(), "test_func");
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Map);
}

TEST(BaseFunctionTest, GettersAndSetters) {
    sage_flow::BaseFunction func("test", sage_flow::FunctionType::None);

    func.setName("new_name");
    EXPECT_EQ(func.getName(), "new_name");

    func.setType(sage_flow::FunctionType::Filter);
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Filter);
}

TEST(BaseFunctionTest, ExecuteSingleInput) {
    sage_flow::BaseFunction func("test", sage_flow::FunctionType::None);
    auto response = sage_flow::createTestResponse({"message1", "message2"});

    auto result = func.execute(response);

    EXPECT_EQ(result.size(), 2);
    EXPECT_EQ(response.size(), 0);  // 原始响应应该被清空
}

TEST(BaseFunctionTest, ExecuteDualInputThrows) {
    sage_flow::BaseFunction func("test", sage_flow::FunctionType::None);
    auto left = sage_flow::createTestResponse({"left"});
    auto right = sage_flow::createTestResponse({"right"});

    EXPECT_THROW(func.execute(left, right), std::runtime_error);
}

// MapFunction测试
TEST(MapFunctionTest, ConstructorWithoutFunc) {
    sage_flow::MapFunction func("map_test");
    EXPECT_EQ(func.getName(), "map_test");
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Map);
}

TEST(MapFunctionTest, ConstructorWithFunc) {
    sage_flow::MapFunc map_func = [](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        if (msg) {
            msg->setMetadata("transformed", "true");
        }
    };

    sage_flow::MapFunction func("map_test", map_func);
    EXPECT_EQ(func.getName(), "map_test");
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Map);
}

TEST(MapFunctionTest, SetMapFunc) {
    sage_flow::MapFunction func("map_test");
    bool called = false;

    sage_flow::MapFunc map_func = [&called](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        called = true;
    };

    func.setMapFunc(map_func);
    auto response = sage_flow::createTestResponse({"test"});
    auto result = func.execute(response);

    EXPECT_TRUE(called);
    EXPECT_EQ(result.size(), 1);
}

TEST(MapFunctionTest, ExecuteWithTransformation) {
    sage_flow::MapFunction func("map_test");

    sage_flow::MapFunc map_func = [](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        if (msg) {
            msg->setMetadata("processed", "true");
            msg->addProcessingStep("map_transform");
        }
    };

    func.setMapFunc(map_func);
    auto response = sage_flow::createTestResponse({"original"});
    auto result = func.execute(response);

    EXPECT_EQ(result.size(), 1);
    EXPECT_EQ(response.size(), 0);

    auto& messages = result.getMessages();
    ASSERT_EQ(messages.size(), 1);
    EXPECT_EQ(messages[0]->getMetadata().at("processed"), "true");
    EXPECT_EQ(messages[0]->getProcessingTrace().back(), "map_transform");
}

TEST(MapFunctionTest, ExecuteWithEmptyResponse) {
    sage_flow::MapFunction func("map_test");
    sage_flow::FunctionResponse response;

    auto result = func.execute(response);

    EXPECT_EQ(result.size(), 0);
    EXPECT_EQ(response.size(), 0);
}

// FilterFunction测试
TEST(FilterFunctionTest, ConstructorWithoutFunc) {
    sage_flow::FilterFunction func("filter_test");
    EXPECT_EQ(func.getName(), "filter_test");
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Filter);
}

TEST(FilterFunctionTest, ConstructorWithFunc) {
    sage_flow::FilterFunc filter_func = [](const sage_flow::MultiModalMessage& msg) {
        return true;
    };

    sage_flow::FilterFunction func("filter_test", filter_func);
    EXPECT_EQ(func.getName(), "filter_test");
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Filter);
}

TEST(FilterFunctionTest, SetFilterFunc) {
    sage_flow::FilterFunction func("filter_test");
    bool called = false;

    sage_flow::FilterFunc filter_func = [&called](const sage_flow::MultiModalMessage& msg) {
        called = true;
        return true;
    };

    func.setFilterFunc(filter_func);
    auto response = sage_flow::createTestResponse({"test"});
    auto result = func.execute(response);

    EXPECT_TRUE(called);
    EXPECT_EQ(result.size(), 1);
}

TEST(FilterFunctionTest, ExecuteWithFilter) {
    sage_flow::FilterFunction func("filter_test");

    // 过滤掉包含"reject"的消息
    sage_flow::FilterFunc filter_func = [](const sage_flow::MultiModalMessage& msg) {
        std::string content = msg.getContentAsString();
        return content.find("reject") == std::string::npos;
    };

    func.setFilterFunc(filter_func);
    auto response = sage_flow::createTestResponse({"accept", "reject", "accept2"});
    auto result = func.execute(response);

    EXPECT_EQ(result.size(), 2);
    EXPECT_EQ(response.size(), 0);

    auto& messages = result.getMessages();
    EXPECT_EQ(messages[0]->getContentAsString(), "accept");
    EXPECT_EQ(messages[1]->getContentAsString(), "accept2");
}

TEST(FilterFunctionTest, ExecuteWithoutFilterFunc) {
    sage_flow::FilterFunction func("filter_test");
    auto response = sage_flow::createTestResponse({"msg1", "msg2"});
    auto result = func.execute(response);

    // 没有过滤函数时，所有消息都应该通过
    EXPECT_EQ(result.size(), 2);
    EXPECT_EQ(response.size(), 0);
}

TEST(FilterFunctionTest, ExecuteWithAllFilteredOut) {
    sage_flow::FilterFunction func("filter_test");

    sage_flow::FilterFunc filter_func = [](const sage_flow::MultiModalMessage& msg) {
        return false;  // 过滤掉所有消息
    };

    func.setFilterFunc(filter_func);
    auto response = sage_flow::createTestResponse({"msg1", "msg2"});
    auto result = func.execute(response);

    EXPECT_EQ(result.size(), 0);
    EXPECT_EQ(response.size(), 0);
}

// SinkFunction测试
TEST(SinkFunctionTest, Constructor) {
    sage_flow::TestSinkFunction func("sink_test");
    EXPECT_EQ(func.getName(), "sink_test");
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Sink);
}

TEST(SinkFunctionTest, ConstructorWithSinkFunc) {
    bool called = false;
    sage_flow::SinkFunc sink_func = [&called](const sage_flow::MultiModalMessage& msg) {
        called = true;
    };

    sage_flow::TestSinkFunction func("sink_test", sink_func);
    EXPECT_EQ(func.getName(), "sink_test");
    EXPECT_EQ(func.getType(), sage_flow::FunctionType::Sink);
}

TEST(SinkFunctionTest, SetSinkFunc) {
    sage_flow::TestSinkFunction func("sink_test");
    bool called = false;

    sage_flow::SinkFunc sink_func = [&called](const sage_flow::MultiModalMessage& msg) {
        called = true;
    };

    func.setSinkFunc(sink_func);
    auto response = sage_flow::createTestResponse({"test"});
    auto result = func.execute(response);

    EXPECT_TRUE(called);
    EXPECT_EQ(result.size(), 0);  // Sink返回空响应
    EXPECT_EQ(response.size(), 0);  // 原始响应被清空
}

TEST(SinkFunctionTest, ExecuteReturnsEmptyResponse) {
    sage_flow::TestSinkFunction func("sink_test");

    sage_flow::SinkFunc sink_func = [](const sage_flow::MultiModalMessage& msg) {
        // 模拟处理消息
    };

    func.setSinkFunc(sink_func);
    auto response = sage_flow::createTestResponse({"msg1", "msg2"});
    auto result = func.execute(response);

    EXPECT_EQ(result.size(), 0);
    EXPECT_EQ(response.size(), 0);
}

TEST(SinkFunctionTest, ExecuteWithEmptyResponse) {
    sage_flow::TestSinkFunction func("sink_test");
    sage_flow::FunctionResponse response;

    auto result = func.execute(response);

    EXPECT_EQ(result.size(), 0);
    EXPECT_EQ(response.size(), 0);
}

TEST(SinkFunctionTest, InitAndClose) {
    sage_flow::TestSinkFunction func("sink_test");

    EXPECT_FALSE(func.initialized_);
    EXPECT_FALSE(func.closed_);

    func.init();
    EXPECT_TRUE(func.initialized_);

    func.close();
    EXPECT_TRUE(func.closed_);
}

// 集成测试
TEST(FunctionIntegrationTest, MapThenFilter) {
    // 创建MapFunction
    sage_flow::MapFunction map_func("map");
    sage_flow::MapFunc map_lambda = [](std::unique_ptr<sage_flow::MultiModalMessage>& msg) {
        if (msg) {
            msg->setMetadata("mapped", "true");
        }
    };
    map_func.setMapFunc(map_lambda);

    // 创建FilterFunction
    sage_flow::FilterFunction filter_func("filter");
    sage_flow::FilterFunc filter_lambda = [](const sage_flow::MultiModalMessage& msg) {
        return msg.getMetadata().count("mapped") > 0;
    };
    filter_func.setFilterFunc(filter_lambda);

    // 执行Map
    auto response = sage_flow::createTestResponse({"test1", "test2"});
    auto map_result = map_func.execute(response);

    // 执行Filter
    auto filter_result = filter_func.execute(map_result);

    EXPECT_EQ(filter_result.size(), 2);
    for (const auto& msg : filter_result.getMessages()) {
        EXPECT_EQ(msg->getMetadata().at("mapped"), "true");
    }
}

TEST(FunctionIntegrationTest, FilterThenSink) {
    // 创建FilterFunction
    sage_flow::FilterFunction filter_func("filter");
    sage_flow::FilterFunc filter_lambda = [](const sage_flow::MultiModalMessage& msg) {
        return msg.getContentAsString() == "keep";
    };
    filter_func.setFilterFunc(filter_lambda);

    // 创建SinkFunction
    sage_flow::TestSinkFunction sink_func("sink");
    int processed_count = 0;
    sage_flow::SinkFunc sink_lambda = [&processed_count](const sage_flow::MultiModalMessage& msg) {
        processed_count++;
    };
    sink_func.setSinkFunc(sink_lambda);

    // 执行Filter
    auto response = sage_flow::createTestResponse({"keep", "discard", "keep"});
    auto filter_result = filter_func.execute(response);

    // 执行Sink
    auto sink_result = sink_func.execute(filter_result);

    EXPECT_EQ(processed_count, 2);
    EXPECT_EQ(sink_result.size(), 0);
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}