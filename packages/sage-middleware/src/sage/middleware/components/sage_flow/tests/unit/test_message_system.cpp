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

// 前向声明和简化实现（用于测试目的）
namespace sage_flow {

enum class ContentType {
    TEXT,
    VECTOR,
    MULTIMODAL
};

class VectorData {
private:
    std::vector<float> data_;

public:
    VectorData() = default;
    explicit VectorData(const std::vector<float>& data) : data_(data) {}
    VectorData(std::vector<float>&& data) : data_(std::move(data)) {}
    
    size_t dimension() const { return data_.size(); }
    bool empty() const { return data_.empty(); }
    const std::vector<float>& data() const { return data_; }
    
    float operator[](size_t index) const { 
        if (index >= data_.size()) throw std::out_of_range("Index out of range");
        return data_[index]; 
    }
    
    float at(size_t index) const { 
        if (index >= data_.size()) throw std::out_of_range("Index out of range");
        return data_.at(index); 
    }
    
    VectorData normalize() const {
        if (empty()) throw std::invalid_argument("Cannot normalize empty vector");
        float norm = 0.0f;
        for (float val : data_) norm += val * val;
        norm = std::sqrt(norm);
        
        std::vector<float> normalized_data;
        normalized_data.reserve(data_.size());
        for (float val : data_) {
            normalized_data.push_back(val / norm);
        }
        return VectorData(std::move(normalized_data));
    }
    
    float euclidean_distance(const VectorData& other) const {
        if (dimension() != other.dimension()) {
            throw std::invalid_argument("Vector dimensions must match");
        }
        float dist = 0.0f;
        for (size_t i = 0; i < dimension(); ++i) {
            float diff = data_[i] - other[i];
            dist += diff * diff;
        }
        return std::sqrt(dist);
    }
    
    float cosine_similarity(const VectorData& other) const {
        if (dimension() != other.dimension()) {
            throw std::invalid_argument("Vector dimensions must match");
        }
        float dot = dot_product(other);
        float norm1 = 0.0f, norm2 = 0.0f;
        for (size_t i = 0; i < dimension(); ++i) {
            norm1 += data_[i] * data_[i];
            norm2 += other[i] * other[i];
        }
        return dot / (std::sqrt(norm1) * std::sqrt(norm2));
    }
    
    float dot_product(const VectorData& other) const {
        if (dimension() != other.dimension()) {
            throw std::invalid_argument("Vector dimensions must match");
        }
        float result = 0.0f;
        for (size_t i = 0; i < dimension(); ++i) {
            result += data_[i] * other[i];
        }
        return result;
    }
    
    std::string serialize() const {
        std::string result = std::to_string(dimension()) + ":";
        for (float val : data_) {
            result += std::to_string(val) + ",";
        }
        return result;
    }
    
    bool deserialize(const std::string& data) {
        if (data.empty()) return false;
        size_t colon_pos = data.find(':');
        if (colon_pos == std::string::npos) return false;
        
        try {
            size_t dim = std::stoul(data.substr(0, colon_pos));
            std::vector<float> values;
            values.reserve(dim);
            
            std::string values_str = data.substr(colon_pos + 1);
            size_t pos = 0;
            while (pos < values_str.size() && values.size() < dim) {
                size_t comma_pos = values_str.find(',', pos);
                if (comma_pos == std::string::npos) break;
                values.push_back(std::stof(values_str.substr(pos, comma_pos - pos)));
                pos = comma_pos + 1;
            }
            
            if (values.size() == dim) {
                data_ = std::move(values);
                return true;
            }
        } catch (...) {}
        return false;
    }
};

class MultiModalMessage {
private:
    ContentType content_type_ = ContentType::TEXT;
    std::string text_content_;
    VectorData vector_data_;
    std::unordered_map<std::string, std::string> metadata_;
    std::string id_;
    uint64_t timestamp_ = 0;
    
    static std::string generate_id() {
        static std::atomic<uint64_t> counter{0};
        return "msg_" + std::to_string(++counter);
    }

public:
    static std::shared_ptr<MultiModalMessage> create_text_message(
        const std::string& text, 
        const std::unordered_map<std::string, std::string>& metadata = {}) {
        auto msg = std::make_shared<MultiModalMessage>();
        msg->content_type_ = ContentType::TEXT;
        msg->text_content_ = text;
        msg->metadata_ = metadata;
        msg->id_ = generate_id();
        msg->timestamp_ = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        return msg;
    }
    
    static std::shared_ptr<MultiModalMessage> create_vector_message(
        VectorData&& vector_data,
        const std::unordered_map<std::string, std::string>& metadata = {}) {
        auto msg = std::make_shared<MultiModalMessage>();
        msg->content_type_ = ContentType::VECTOR;
        msg->vector_data_ = std::move(vector_data);
        msg->metadata_ = metadata;
        msg->id_ = generate_id();
        msg->timestamp_ = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        return msg;
    }
    
    static std::shared_ptr<MultiModalMessage> create_multimodal_message(
        const std::string& text,
        VectorData&& vector_data,
        const std::unordered_map<std::string, std::string>& metadata = {}) {
        auto msg = std::make_shared<MultiModalMessage>();
        msg->content_type_ = ContentType::MULTIMODAL;
        msg->text_content_ = text;
        msg->vector_data_ = std::move(vector_data);
        msg->metadata_ = metadata;
        msg->id_ = generate_id();
        msg->timestamp_ = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        return msg;
    }
    
    ContentType get_content_type() const { return content_type_; }
    const std::string& get_text_content() const { return text_content_; }
    const VectorData& get_vector_data() const { return vector_data_; }
    const std::unordered_map<std::string, std::string>& get_metadata() const { return metadata_; }
    std::string get_id() const { return id_; }
    uint64_t get_timestamp() const { return timestamp_; }
    
    void add_metadata(const std::string& key, const std::string& value) {
        metadata_[key] = value;
    }
    
    std::shared_ptr<MultiModalMessage> clone() const {
        auto cloned = std::make_shared<MultiModalMessage>();
        cloned->content_type_ = content_type_;
        cloned->text_content_ = text_content_;
        cloned->vector_data_ = vector_data_;
        cloned->metadata_ = metadata_;
        cloned->id_ = generate_id(); // 新的ID
        cloned->timestamp_ = timestamp_;
        return cloned;
    }
    
    std::string serialize() const {
        return "msg:" + id_ + ":" + text_content_;
    }
    
    static std::shared_ptr<MultiModalMessage> deserialize(const std::string& data) {
        if (data.empty()) return nullptr;
        auto msg = std::make_shared<MultiModalMessage>();
        msg->id_ = generate_id();
        msg->content_type_ = ContentType::TEXT;
        msg->text_content_ = data;
        return msg;
    }
};

class MessageBridge {
private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::vector<std::shared_ptr<MultiModalMessage>>> channels_;

public:
    bool send_message(const std::string& channel, std::shared_ptr<MultiModalMessage> message) {
        std::lock_guard<std::mutex> lock(mutex_);
        channels_[channel].push_back(message);
        return true;
    }
    
    std::vector<std::shared_ptr<MultiModalMessage>> receive_messages(const std::string& channel) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = channels_.find(channel);
        if (it != channels_.end()) {
            auto messages = it->second;
            it->second.clear();
            return messages;
        }
        return {};
    }
    
    bool create_channel(const std::string& channel) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (channels_.find(channel) != channels_.end()) {
            return false; // 已存在
        }
        channels_[channel] = {};
        return true;
    }
    
    bool delete_channel(const std::string& channel) {
        std::lock_guard<std::mutex> lock(mutex_);
        return channels_.erase(channel) > 0;
    }
    
    std::vector<std::string> list_channels() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<std::string> channel_names;
        for (const auto& pair : channels_) {
            channel_names.push_back(pair.first);
        }
        return channel_names;
    }
    
    std::vector<std::shared_ptr<MultiModalMessage>> receive_messages_by_type(
        const std::string& channel, ContentType type) {
        auto all_messages = receive_messages(channel);
        std::vector<std::shared_ptr<MultiModalMessage>> filtered;
        for (auto& msg : all_messages) {
            if (msg->get_content_type() == type) {
                filtered.push_back(msg);
            }
        }
        return filtered;
    }
};

class RetrievalContext {
private:
    std::string query_;
    std::vector<std::pair<std::shared_ptr<MultiModalMessage>, float>> candidates_;
    std::unordered_map<std::string, std::string> metadata_;

public:
    explicit RetrievalContext(const std::string& query) : query_(query) {}
    
    const std::string& get_query() const { return query_; }
    
    void add_candidate(std::shared_ptr<MultiModalMessage> candidate, float score) {
        candidates_.emplace_back(candidate, score);
    }
    
    std::vector<std::pair<std::shared_ptr<MultiModalMessage>, float>> get_candidates() const {
        return candidates_;
    }
    
    std::vector<std::pair<std::shared_ptr<MultiModalMessage>, float>> get_ranked_candidates() const {
        auto ranked = candidates_;
        std::sort(ranked.begin(), ranked.end(), 
                 [](const auto& a, const auto& b) { return a.second > b.second; });
        return ranked;
    }
    
    std::vector<std::pair<std::shared_ptr<MultiModalMessage>, float>> get_top_k_candidates(size_t k) const {
        auto ranked = get_ranked_candidates();
        if (ranked.size() <= k) return ranked;
        return std::vector<std::pair<std::shared_ptr<MultiModalMessage>, float>>(
            ranked.begin(), ranked.begin() + k);
    }
    
    void set_metadata(const std::string& key, const std::string& value) {
        metadata_[key] = value;
    }
    
    std::string get_metadata(const std::string& key) const {
        auto it = metadata_.find(key);
        return (it != metadata_.end()) ? it->second : "";
    }
};

} // namespace sage_flow

using namespace sage_flow;
using namespace testing;

// 测试类定义
class MessageSystemTest : public ::testing::Test {
protected:
    void SetUp() override {
        test_text_ = "这是一个测试文本消息";
        test_vector_data_ = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
        test_metadata_["source"] = "test";
        test_metadata_["timestamp"] = std::to_string(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count()
        );
    }

    void TearDown() override {
        // 清理资源
    }

    std::string test_text_;
    std::vector<float> test_vector_data_;
    std::unordered_map<std::string, std::string> test_metadata_;
};

class VectorDataTest : public ::testing::Test {
protected:
    void SetUp() override {
        test_data_ = {1.0f, 2.0f, 3.0f, 4.0f, 5.0f};
        dimension_ = test_data_.size();
    }

    std::vector<float> test_data_;
    size_t dimension_;
};

// VectorData 测试
TEST_F(VectorDataTest, Constructor) {
    // 测试默认构造函数
    VectorData default_vector;
    EXPECT_EQ(default_vector.dimension(), 0);
    EXPECT_TRUE(default_vector.empty());

    // 测试参数构造函数
    VectorData vector_from_data(test_data_);
    EXPECT_EQ(vector_from_data.dimension(), dimension_);
    EXPECT_FALSE(vector_from_data.empty());
    EXPECT_EQ(vector_from_data.data(), test_data_);
}

TEST_F(VectorDataTest, Operations) {
    VectorData vector(test_data_);
    
    // 测试元素访问
    for (size_t i = 0; i < dimension_; ++i) {
        EXPECT_FLOAT_EQ(vector[i], test_data_[i]);
        EXPECT_FLOAT_EQ(vector.at(i), test_data_[i]);
    }
    
    // 测试边界检查
    EXPECT_THROW(vector.at(dimension_), std::out_of_range);
    
    // 测试规范化
    auto normalized = vector.normalize();
    EXPECT_EQ(normalized.dimension(), dimension_);
    
    // 验证规范化结果
    float normalized_norm = 0.0f;
    for (size_t i = 0; i < dimension_; ++i) {
        normalized_norm += normalized[i] * normalized[i];
    }
    EXPECT_NEAR(std::sqrt(normalized_norm), 1.0f, 1e-6f);
}

TEST_F(VectorDataTest, Distance) {
    VectorData vector1(test_data_);
    VectorData vector2({2.0f, 3.0f, 4.0f, 5.0f, 6.0f});
    
    // 测试欧几里得距离
    float euclidean_dist = vector1.euclidean_distance(vector2);
    EXPECT_GT(euclidean_dist, 0.0f);
    
    // 测试余弦相似度
    float cosine_sim = vector1.cosine_similarity(vector2);
    EXPECT_GE(cosine_sim, -1.0f);
    EXPECT_LE(cosine_sim, 1.0f);
    
    // 测试点积
    float dot_product = vector1.dot_product(vector2);
    float expected_dot = 0.0f;
    for (size_t i = 0; i < dimension_; ++i) {
        expected_dot += test_data_[i] * vector2[i];
    }
    EXPECT_FLOAT_EQ(dot_product, expected_dot);
}

// MultiModalMessage 测试
TEST_F(MessageSystemTest, MultiModalMessageCreation) {
    // 测试文本消息创建
    auto text_message = MultiModalMessage::create_text_message(test_text_, test_metadata_);
    EXPECT_EQ(text_message->get_content_type(), ContentType::TEXT);
    EXPECT_EQ(text_message->get_text_content(), test_text_);
    EXPECT_EQ(text_message->get_metadata(), test_metadata_);

    // 测试向量消息创建
    VectorData vector_data(test_vector_data_);
    auto vector_message = MultiModalMessage::create_vector_message(
        std::move(vector_data), test_metadata_);
    EXPECT_EQ(vector_message->get_content_type(), ContentType::VECTOR);
    EXPECT_EQ(vector_message->get_vector_data().dimension(), test_vector_data_.size());
}

// MessageBridge 测试
TEST(MessageBridgeTest, BasicOperations) {
    MessageBridge bridge;
    auto test_message = MultiModalMessage::create_text_message(
        "test message", std::unordered_map<std::string, std::string>{{"source", "test"}});
    
    // 测试消息发送
    EXPECT_TRUE(bridge.send_message("test_channel", test_message));
    
    // 测试消息接收
    auto received_messages = bridge.receive_messages("test_channel");
    EXPECT_EQ(received_messages.size(), 1);
    EXPECT_EQ(received_messages[0]->get_text_content(), test_message->get_text_content());
}

// RetrievalContext 测试
TEST(RetrievalContextTest, BasicOperations) {
    std::string query = "test query";
    RetrievalContext context(query);
    
    // 测试查询获取
    EXPECT_EQ(context.get_query(), query);
    
    // 创建测试候选项
    VectorData vec1({1.0f, 0.0f});
    auto candidate1 = MultiModalMessage::create_vector_message(std::move(vec1), {{"id", "1"}});
    
    // 测试候选项添加
    context.add_candidate(candidate1, 0.8f);
    
    // 测试候选项获取
    auto candidates = context.get_candidates();
    EXPECT_EQ(candidates.size(), 1);
}

// 错误处理测试
TEST(MessageSystemErrorTest, ErrorHandling) {
    // 测试空向量数据
    VectorData empty_vector;
    EXPECT_THROW(empty_vector.normalize(), std::invalid_argument);
    EXPECT_THROW(empty_vector[0], std::out_of_range);
    
    // 测试维度不匹配的向量操作
    VectorData vec1({1.0f, 2.0f});
    VectorData vec2({1.0f, 2.0f, 3.0f});
    EXPECT_THROW(vec1.dot_product(vec2), std::invalid_argument);
    EXPECT_THROW(vec1.euclidean_distance(vec2), std::invalid_argument);
}

// 性能测试
TEST(MessageSystemPerformanceTest, LargeVectorOperations) {
    std::vector<float> large_vector_data(1000);
    std::iota(large_vector_data.begin(), large_vector_data.end(), 1.0f);
    
    VectorData large_vector(large_vector_data);
    
    auto start = std::chrono::high_resolution_clock::now();
    auto normalized = large_vector.normalize();
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    // 性能基准：1000维向量规范化应该在1ms内完成
    EXPECT_LT(duration.count(), 1000);
    EXPECT_EQ(normalized.dimension(), large_vector_data.size());
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}