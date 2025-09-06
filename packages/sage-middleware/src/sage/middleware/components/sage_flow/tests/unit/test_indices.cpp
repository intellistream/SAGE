/**
 * @file test_indices.cpp
 * @brief 索引系统单元测试
 *
 * 测试 HNSW, IVF, BruteForce 等索引组件
 */

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <memory>
#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <filesystem>

#include "index/brute_force_index.hpp"
#include "index/index_types.hpp"
#include "memory/memory_pool.hpp"

namespace fs = std::filesystem;
using namespace sage_flow;

// 基础测试框架
TEST(IndexTest, FrameworkSetup) {
    // 验证Google Test框架正常工作
    EXPECT_TRUE(true);
}

TEST(IndexTest, BasicAssertions) {
    std::vector<float> test_vector = {1.0f, 2.0f, 3.0f};
    EXPECT_EQ(test_vector.size(), 3);
    EXPECT_FALSE(test_vector.empty());
}

// BruteForceIndex 测试
class BruteForceIndexTest : public ::testing::Test {
protected:
    void SetUp() override {
        memory_pool_ = CreateDefaultMemoryPool();
        index_ = std::make_unique<BruteForceIndex>(memory_pool_);

        IndexConfig config;
        config.dimension_ = 3;
        config.distance_metric_ = "cosine";
        ASSERT_TRUE(index_->Initialize(config));
    }

    std::shared_ptr<MemoryPool> memory_pool_;
    std::unique_ptr<BruteForceIndex> index_;
};

TEST_F(BruteForceIndexTest, Initialization) {
    EXPECT_EQ(index_->GetType(), IndexType::kBruteForce);
    EXPECT_EQ(index_->Size(), 0);
}

TEST_F(BruteForceIndexTest, AddAndSearchVectors) {
    // 添加测试向量
    std::vector<float> vec1 = {1.0f, 0.0f, 0.0f};
    std::vector<float> vec2 = {0.0f, 1.0f, 0.0f};
    std::vector<float> vec3 = {0.0f, 0.0f, 1.0f};

    EXPECT_TRUE(index_->AddVector(1, vec1));
    EXPECT_TRUE(index_->AddVector(2, vec2));
    EXPECT_TRUE(index_->AddVector(3, vec3));

    EXPECT_EQ(index_->Size(), 3);

    // 搜索最相似的向量
    std::vector<float> query = {1.0f, 0.0f, 0.0f};
    auto results = index_->Search(query, 2);

    ASSERT_EQ(results.size(), 2);
    EXPECT_EQ(results[0].id_, 1);  // 最相似的应该是自己
    EXPECT_FLOAT_EQ(results[0].similarity_score_, 1.0f);
}

TEST_F(BruteForceIndexTest, RemoveVector) {
    std::vector<float> vec = {1.0f, 2.0f, 3.0f};
    EXPECT_TRUE(index_->AddVector(1, vec));
    EXPECT_EQ(index_->Size(), 1);

    EXPECT_TRUE(index_->RemoveVector(1));
    EXPECT_EQ(index_->Size(), 0);

    // 移除不存在的向量应该返回false
    EXPECT_FALSE(index_->RemoveVector(999));
}

TEST_F(BruteForceIndexTest, BuildIndex) {
    // BruteForce不需要构建，但应该返回true
    EXPECT_TRUE(index_->Build());
}

TEST_F(BruteForceIndexTest, ClearIndex) {
    std::vector<float> vec = {1.0f, 2.0f, 3.0f};
    EXPECT_TRUE(index_->AddVector(1, vec));
    EXPECT_EQ(index_->Size(), 1);

    index_->Clear();
    EXPECT_EQ(index_->Size(), 0);
}

TEST_F(BruteForceIndexTest, SaveAndLoadIndex) {
    // 添加一些向量
    std::vector<float> vec1 = {1.0f, 0.0f, 0.0f};
    std::vector<float> vec2 = {0.0f, 1.0f, 0.0f};
    EXPECT_TRUE(index_->AddVector(1, vec1));
    EXPECT_TRUE(index_->AddVector(2, vec2));

    // 保存索引
    std::string test_file = "test_brute_force_index.bin";
    EXPECT_TRUE(index_->SaveIndex(test_file));

    // 创建新索引并加载
    auto new_index = std::make_unique<BruteForceIndex>(memory_pool_);
    IndexConfig config;
    config.dimension_ = 3;
    config.distance_metric_ = "cosine";
    ASSERT_TRUE(new_index->Initialize(config));

    EXPECT_TRUE(new_index->LoadIndex(test_file));
    EXPECT_EQ(new_index->Size(), 2);

    // 验证加载的数据
    auto results = new_index->Search(vec1, 1);
    ASSERT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].id_, 1);

    // 清理测试文件
    if (fs::exists(test_file)) {
        fs::remove(test_file);
    }
}

TEST_F(BruteForceIndexTest, SearchEmptyIndex) {
    std::vector<float> query = {1.0f, 2.0f, 3.0f};
    auto results = index_->Search(query, 5);
    EXPECT_TRUE(results.empty());
}

TEST_F(BruteForceIndexTest, SearchWithKGreaterThanSize) {
    std::vector<float> vec1 = {1.0f, 0.0f, 0.0f};
    std::vector<float> vec2 = {0.0f, 1.0f, 0.0f};
    EXPECT_TRUE(index_->AddVector(1, vec1));
    EXPECT_TRUE(index_->AddVector(2, vec2));

    std::vector<float> query = {0.5f, 0.5f, 0.0f};
    auto results = index_->Search(query, 10);  // 请求10个，但只有2个向量

    ASSERT_EQ(results.size(), 2);

    // 验证返回了正确的ID（顺序可能不稳定，因为相似度相等）
    std::set<uint64_t> expected_ids = {1, 2};
    std::set<uint64_t> actual_ids;
    for (const auto& result : results) {
        actual_ids.insert(result.id_);
    }
    EXPECT_EQ(actual_ids, expected_ids);

    // 验证相似度分数合理
    for (const auto& result : results) {
        EXPECT_GE(result.similarity_score_, 0.0f);
        EXPECT_LE(result.similarity_score_, 1.0f);
    }
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}