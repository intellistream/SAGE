#include <gtest/gtest.h>
#include <fstream>
#include <sstream>
#include <vector>
#include <memory>
#include "data_stream/data_stream.hpp"
#include "operator/map_operator.hpp"
#include "operator/filter_operator.hpp"
#include "operator/file_sink_operator.hpp"
#include "engine/stream_engine.hpp"
#include "message/multimodal_message.hpp"
#include "sources/file_data_source.hpp"

using namespace sage_flow;

class PipelineIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        input_file = "tests/data/test_data.csv";
        output_file = "tests/data/test_pipeline_output.csv";
        engine = std::make_shared<StreamEngine>();
    }

    std::string input_file;
    std::string output_file;
    std::shared_ptr<StreamEngine> engine;
};

// 辅助函数：读取CSV文件到MultiModalMessage向量
std::vector<std::shared_ptr<MultiModalMessage>> read_csv_to_messages(const std::string& filename) {
    std::vector<std::shared_ptr<MultiModalMessage>> messages;
    std::ifstream file(filename);
    std::string line;
    std::getline(file, line); // 跳过头行
    while (std::getline(file, line)) {
        std::istringstream iss(line);
        std::string id, value, text;
        std::getline(iss, id, ',');
        std::getline(iss, value, ',');
        std::getline(iss, text, ',');
        auto msg = std::make_shared<MultiModalMessage>();
        msg->set_content_as_string("ID:" + id + ", Value:" + value + ", Text:" + text);
        messages.push_back(msg);
    }
    return messages;
}

// 辅助函数：验证输出CSV
void verify_output(const std::string& filename, int expected_lines) {
    std::ifstream file(filename);
    std::string line;
    int count = 0;
    while (std::getline(file, line)) {
        count++;
    }
    ASSERT_EQ(count, expected_lines);
    // 进一步验证内容（简化）
    file.clear();
    file.seekg(0);
    std::getline(file, line); // 头行
    std::getline(file, line);
    ASSERT_NE(line.find("Value:20"), std::string::npos); // 过滤后应有20
}

TEST_F(PipelineIntegrationTest, BasicPipelineTest) {
    // 步骤1: 从CSV创建DataStream
    auto source = std::make_shared<FileDataSource>(input_file);
    auto data_stream = DataStream::from_source(source);

    // 步骤2: 应用Map - 乘以2
    auto map_op = std::make_shared<MapOperator>("map_multiply", [](const std::shared_ptr<MultiModalMessage>& msg) -> std::shared_ptr<MultiModalMessage> {
        auto content = msg->get_content_as_string();
        // 解析value并乘2
        size_t pos = content.find("Value:");
        if (pos != std::string::npos) {
            std::string value_str = content.substr(pos + 6);
            size_t comma = value_str.find(",");
            if (comma != std::string::npos) {
                value_str = value_str.substr(0, comma);
            }
            int value = std::stoi(value_str);
            value *= 2;
            // 替换value
            std::string new_content = content;
            size_t start = pos + 6;
            size_t end = content.find(",", start);
            if (end == std::string::npos) end = content.size();
            new_content.replace(start, end - start, std::to_string(value));
            auto new_msg = std::make_shared<MultiModalMessage>();
            new_msg->set_content_as_string(new_content);
            return new_msg;
        }
        return msg;
    });
    data_stream = data_stream.map(map_op);

    // 步骤3: 应用Filter - value > 15 (原始>7.5，但乘2后>15)
    auto filter_op = std::make_shared<FilterOperator>("filter_large", [](const std::shared_ptr<MultiModalMessage>& msg) -> bool {
        auto content = msg->get_content_as_string();
        size_t pos = content.find("Value:");
        if (pos != std::string::npos) {
            std::string value_str = content.substr(pos + 6);
            size_t comma = value_str.find(",");
            if (comma != std::string::npos) {
                value_str = value_str.substr(0, comma);
            }
            int value = std::stoi(value_str);
            return value > 15;
        }
        return false;
    });
    data_stream = data_stream.filter(filter_op);

    // 步骤4: Sink到文件
    auto sink_op = std::make_shared<FileSinkOperator>("file_sink", output_file);
    data_stream = data_stream.sink(sink_op);

    // 步骤5: 执行管道
    auto result = engine->execute(data_stream.getGraph());
    ASSERT_TRUE(result.has_value());

    // 步骤6: 验证输出
    verify_output(output_file, 3); // 原始5条，过滤后3条 (20,30,50 >15)
}

TEST_F(PipelineIntegrationTest, EmptyInputPipeline) {
    // 创建空输入文件测试
    std::ofstream empty_file("tests/data/empty.csv");
    empty_file << "id,value,text\n";
    empty_file.close();

    auto source = std::make_shared<FileDataSource>("tests/data/empty.csv");
    auto data_stream = DataStream::from_source(source);
    auto map_op = std::make_shared<MapOperator>("map", [](const std::shared_ptr<MultiModalMessage>&) -> std::shared_ptr<MultiModalMessage> {
        return nullptr; // 简化
    });
    data_stream = data_stream.map(map_op);
    auto sink_op = std::make_shared<FileSinkOperator>("sink", "tests/data/empty_output.csv");
    data_stream = data_stream.sink(sink_op);

    auto result = engine->execute(data_stream.getGraph());
    ASSERT_TRUE(result.has_value());

    // 验证输出为空
    std::ifstream out("tests/data/empty_output.csv");
    std::string content((std::istreambuf_iterator<char>(out)), std::istreambuf_iterator<char>());
    ASSERT_EQ(content, "id,value,text\n"); // 只头行
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}