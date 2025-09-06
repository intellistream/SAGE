/**
 * @file test_message_system.cpp
 * @brief 消息系统单元测试
 *
 * 测试 MultiModalMessage, MessageBridge, VectorData 等核心消息组件
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <memory>
#include <vector>
#include <string>
#include <chrono>
#include <unordered_map>
#include <thread>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <atomic>
#include <mutex>
#include <filesystem>

#include "../../include/message/multimodal_message.hpp"
#include "../../include/message/content_type.hpp"
#include "../../include/message/vector_data.hpp"

using namespace testing;
using namespace sage_flow;


// MultiModalMessage 测试
class MultiModalMessageTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建测试消息
        message_ = std::make_unique<MultiModalMessage>(12345, ContentType::kText, "Hello World");
    }

    std::unique_ptr<MultiModalMessage> message_;
};

TEST_F(MultiModalMessageTest, ConstructorWithUidAndContent) {
    EXPECT_EQ(message_->getUid(), 12345);
    EXPECT_EQ(message_->getContentType(), ContentType::kText);
    EXPECT_EQ(message_->getContentAsString(), "Hello World");
    EXPECT_FALSE(message_->getSageUid().empty());
}

TEST_F(MultiModalMessageTest, ConstructorWithSageUid) {
    std::string sage_uid = "sage_12345";
    auto msg = std::make_unique<MultiModalMessage>(sage_uid, ContentType::kText, "Test");
    EXPECT_EQ(msg->getSageUid(), sage_uid);
    EXPECT_EQ(msg->getContentAsString(), "Test");
}

TEST_F(MultiModalMessageTest, ContentTypeOperations) {
    message_->setContentType(ContentType::kBinary);
    EXPECT_EQ(message_->getContentType(), ContentType::kBinary);

    std::vector<uint8_t> binary_data = {0x01, 0x02, 0x03};
    message_->setContent(binary_data);
    EXPECT_EQ(message_->getContentType(), ContentType::kBinary);
    EXPECT_EQ(message_->getContentAsBinary(), binary_data);
}

TEST_F(MultiModalMessageTest, MetadataOperations) {
    message_->setMetadata("key1", "value1");
    message_->setMetadata("key2", "value2");

    auto metadata = message_->getMetadata();
    EXPECT_EQ(metadata.size(), 2);
    EXPECT_EQ(metadata.at("key1"), "value1");
    EXPECT_EQ(metadata.at("key2"), "value2");
}

TEST_F(MultiModalMessageTest, ProcessingTrace) {
    message_->addProcessingStep("step1");
    message_->addProcessingStep("step2");

    auto trace = message_->getProcessingTrace();
    EXPECT_EQ(trace.size(), 2);
    EXPECT_EQ(trace[0], "step1");
    EXPECT_EQ(trace[1], "step2");
}

TEST_F(MultiModalMessageTest, QualityScore) {
    EXPECT_FALSE(message_->getQualityScore().has_value());

    message_->setQualityScore(0.95f);
    ASSERT_TRUE(message_->getQualityScore().has_value());
    EXPECT_FLOAT_EQ(message_->getQualityScore().value(), 0.95f);
}

TEST_F(MultiModalMessageTest, EmbeddingOperations) {
    EXPECT_FALSE(message_->hasEmbedding());

    std::vector<float> embedding_data = {0.1f, 0.2f, 0.3f};
    VectorData embedding(embedding_data, 3);
    message_->setEmbedding(std::move(embedding));

    EXPECT_TRUE(message_->hasEmbedding());
    ASSERT_TRUE(message_->getEmbedding().has_value());
    EXPECT_EQ(message_->getEmbedding()->getData(), std::vector<float>({0.1f, 0.2f, 0.3f}));
}

TEST_F(MultiModalMessageTest, SourceAndTags) {
    message_->setSource("test_source");
    EXPECT_EQ(message_->getSource(), "test_source");

    message_->addTag("tag1");
    message_->addTag("tag2");
    EXPECT_TRUE(message_->hasTag("tag1"));
    EXPECT_TRUE(message_->hasTag("tag2"));
    EXPECT_FALSE(message_->hasTag("nonexistent"));

    message_->removeTag("tag1");
    EXPECT_FALSE(message_->hasTag("tag1"));
    EXPECT_TRUE(message_->hasTag("tag2"));
}

TEST_F(MultiModalMessageTest, CustomFields) {
    message_->setCustomField("field1", "value1");
    message_->setCustomField("field2", "value2");

    EXPECT_EQ(message_->getCustomField("field1"), "value1");
    EXPECT_EQ(message_->getCustomField("field2"), "value2");
    EXPECT_EQ(message_->getCustomField("nonexistent", "default"), "default");

    message_->removeCustomField("field1");
    EXPECT_EQ(message_->getCustomField("field1", "default"), "default");
}

TEST_F(MultiModalMessageTest, ProcessedState) {
    EXPECT_FALSE(message_->isProcessed());
    EXPECT_FALSE(message_->getProcessedTimestamp().has_value());

    message_->setProcessed(true);
    EXPECT_TRUE(message_->isProcessed());
    ASSERT_TRUE(message_->getProcessedTimestamp().has_value());
}

TEST_F(MultiModalMessageTest, ContentValidation) {
    EXPECT_TRUE(message_->isTextContent());
    EXPECT_FALSE(message_->isBinaryContent());

    std::vector<uint8_t> binary_data = {0x01, 0x02, 0x03};
    message_->setContent(binary_data);
    EXPECT_FALSE(message_->isTextContent());
    EXPECT_TRUE(message_->isBinaryContent());
}

TEST_F(MultiModalMessageTest, CloneOperation) {
    message_->setMetadata("test", "value");
    message_->addTag("cloned");

    auto cloned = message_->clone();
    ASSERT_TRUE(cloned);

    EXPECT_EQ(cloned->getUid(), message_->getUid());
    EXPECT_EQ(cloned->getContentType(), message_->getContentType());
    EXPECT_EQ(cloned->getContentAsString(), message_->getContentAsString());
    EXPECT_TRUE(cloned->hasTag("cloned"));
}

TEST_F(MultiModalMessageTest, MoveSemantics) {
    auto moved_message = std::make_unique<MultiModalMessage>(
        67890, ContentType::kText, "Moved Content");

    // 测试移动构造函数
    MultiModalMessage moved(std::move(*moved_message));
    EXPECT_EQ(moved.getUid(), 67890);
    EXPECT_EQ(moved.getContentAsString(), "Moved Content");
}

TEST_F(MultiModalMessageTest, TimestampOperations) {
    auto initial_timestamp = message_->getTimestamp();
    EXPECT_GT(initial_timestamp, 0);

    // 时间戳应该在合理范围内（当前时间前后几秒）
    auto now = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    EXPECT_NEAR(initial_timestamp, now, 5000);  // 5秒容差
}

TEST(MessageSystemTest, ContentTypeEnum) {
    EXPECT_EQ(static_cast<uint8_t>(ContentType::kText), 0);
    EXPECT_EQ(static_cast<uint8_t>(ContentType::kBinary), 1);
    EXPECT_EQ(static_cast<uint8_t>(ContentType::kImage), 2);
    EXPECT_EQ(static_cast<uint8_t>(ContentType::kAudio), 3);
    EXPECT_EQ(static_cast<uint8_t>(ContentType::kVideo), 4);
    EXPECT_EQ(static_cast<uint8_t>(ContentType::kEmbedding), 5);
    EXPECT_EQ(static_cast<uint8_t>(ContentType::kMetadata), 6);
}

// VectorData 测试
TEST(VectorDataTest, ConstructorAndAccess) {
    std::vector<float> data = {1.0f, 2.0f, 3.0f, 4.0f};
    VectorData vec(data, 4);

    EXPECT_EQ(vec.getData(), data);
    EXPECT_EQ(vec.size(), 4);
    EXPECT_GT(vec.size(), 0);
}

TEST(VectorDataTest, EmptyVector) {
    std::vector<float> empty_data = {};
    VectorData vec(empty_data, 0);
    EXPECT_EQ(vec.size(), 0);
}

TEST(VectorDataTest, Normalization) {
    std::vector<float> data = {3.0f, 4.0f};  // 长度为5
    VectorData vec(data, 2);

    // 测试向量操作
    EXPECT_EQ(vec.size(), 2);
    EXPECT_EQ(vec.getData()[0], 3.0f);
    EXPECT_EQ(vec.getData()[1], 4.0f);
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}