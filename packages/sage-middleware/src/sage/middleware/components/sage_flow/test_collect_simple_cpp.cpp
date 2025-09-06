#include <iostream>
#include <memory>
#include <vector>
#include <string>

// 使用真正的SAGE Flow实现进行测试
#include "include/data_stream/data_stream.hpp"
#include "include/engine/stream_engine.hpp"
#include "include/engine/execution_graph.hpp"
#include "include/message/multimodal_message.hpp"
#include "include/message/content_type.hpp"

using namespace sage_flow;

int main() {
    std::cout << "=== C++ collect() 测试 ===" << std::endl;

    try {
        // 创建引擎和图
        auto engine = std::make_shared<StreamEngine>();
        auto graph = std::make_shared<ExecutionGraph>();

        // 创建DataStream实例
        DataStream stream(engine, graph);

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
        auto results = stream.collect();
        std::cout << "collect()成功，返回 " << results.size() << " 条消息" << std::endl;

        // 验证结果
        if (results.size() != 3) {
            std::cout << "错误：期望3条消息，实际得到" << results.size() << "条" << std::endl;
            return 1;
        }

        for (size_t i = 0; i < results.size(); ++i) {
            if (!results[i]) {
                std::cout << "错误：消息 " << i << " 为空" << std::endl;
                return 1;
            }

            if (results[i]->getContentType() != ContentType::kText) {
                std::cout << "错误：消息 " << i << " 内容类型不正确" << std::endl;
                return 1;
            }

            std::string content = std::get<std::string>(results[i]->getContent());
            std::cout << "消息 " << i << ": " << content << std::endl;
        }

        std::cout << "✅ C++ collect() 测试通过" << std::endl;
        return 0;

    } catch (const std::exception& e) {
        std::cout << "❌ collect()失败: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cout << "❌ collect()发生未知错误" << std::endl;
        return 1;
    }
}