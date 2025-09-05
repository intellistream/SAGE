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

// 简化的索引测试实现
namespace sage_flow {

// 向量数据结构
struct Vector {
    std::vector<float> data;
    std::string id;
    
    Vector(const std::vector<float>& d, const std::string& i) : data(d), id(i) {}
    
    float distance(const Vector& other) const {
        float dist = 0.0f;
        for (size_t i = 0; i < data.size() && i < other.data.size(); ++i) {
            float diff = data[i] - other.data[i];
            dist += diff * diff;
        }
        return std::sqrt(dist);
    }
};

// 搜索结果
struct SearchResult {
    std::string id;
    float distance;
    
    // 默认构造函数
    SearchResult() : id(""), distance(0.0f) {}
    
    SearchResult(const std::string& i, float d) : id(i), distance(d) {}
};

// 基础索引接口
class Index {
public:
    virtual ~Index() = default;
    virtual bool add_vector(const Vector& vector) = 0;
    virtual std::vector<SearchResult> search(const Vector& query, size_t k) = 0;
    virtual size_t size() const = 0;
    virtual std::string get_type() const = 0;
};

// 暴力搜索索引
class BruteForceIndex : public Index {
public:
    bool add_vector(const Vector& vector) override {
        vectors_.push_back(vector);
        return true;
    }
    
    std::vector<SearchResult> search(const Vector& query, size_t k) override {
        std::vector<SearchResult> results;
        
        // 计算与所有向量的距离
        for (const auto& vec : vectors_) {
            float dist = query.distance(vec);
            results.emplace_back(vec.id, dist);
        }
        
        // 按距离排序
        std::sort(results.begin(), results.end(), 
                 [](const SearchResult& a, const SearchResult& b) {
                     return a.distance < b.distance;
                 });
        
        // 返回top-k结果
        if (results.size() > k) {
            results.resize(k);
        }
        
        return results;
    }
    
    size_t size() const override { return vectors_.size(); }
    std::string get_type() const override { return "brute_force"; }

private:
    std::vector<Vector> vectors_;
};

// HNSW 索引（简化版）
class HNSWIndex : public Index {
public:
    explicit HNSWIndex(size_t max_connections = 16) 
        : max_connections_(max_connections) {}
    
    bool add_vector(const Vector& vector) override {
        vectors_.push_back(vector);
        
        // 简化的图构建逻辑
        if (vectors_.size() > 1) {
            build_connections(vectors_.size() - 1);
        }
        
        return true;
    }
    
    std::vector<SearchResult> search(const Vector& query, size_t k) override {
        if (vectors_.empty()) return {};
        
        // 简化的HNSW搜索：从随机起点开始贪心搜索
        std::vector<SearchResult> candidates;
        std::vector<bool> visited(vectors_.size(), false);
        
        // 随机选择起点
        size_t start_idx = 0;
        if (vectors_.size() > 1) {
            start_idx = static_cast<size_t>(rand()) % vectors_.size();
        }
        
        // 贪心搜索
        candidates.emplace_back(vectors_[start_idx].id, 
                              query.distance(vectors_[start_idx]));
        visited[start_idx] = true;
        
        // 扩展搜索
        for (size_t i = 0; i < std::min(k * 2, vectors_.size()); ++i) {
            size_t best_idx = find_closest_unvisited(query, visited);
            if (best_idx < vectors_.size()) {
                candidates.emplace_back(vectors_[best_idx].id, 
                                      query.distance(vectors_[best_idx]));
                visited[best_idx] = true;
            }
        }
        
        // 排序并返回top-k
        std::sort(candidates.begin(), candidates.end(),
                 [](const SearchResult& a, const SearchResult& b) {
                     return a.distance < b.distance;
                 });
        
        if (candidates.size() > k) {
            candidates.resize(k);
        }
        
        return candidates;
    }
    
    size_t size() const override { return vectors_.size(); }
    std::string get_type() const override { return "hnsw"; }

private:
    size_t max_connections_;
    std::vector<Vector> vectors_;
    std::vector<std::vector<size_t>> connections_;
    
    void build_connections(size_t new_idx) {
        if (connections_.size() <= new_idx) {
            connections_.resize(new_idx + 1);
        }
        
        // 简化的连接构建：连接到最近的几个节点
        std::vector<std::pair<float, size_t>> distances;
        
        for (size_t i = 0; i < new_idx; ++i) {
            float dist = vectors_[new_idx].distance(vectors_[i]);
            distances.emplace_back(dist, i);
        }
        
        std::sort(distances.begin(), distances.end());
        
        size_t num_connections = std::min(max_connections_, distances.size());
        for (size_t i = 0; i < num_connections; ++i) {
            size_t neighbor_idx = distances[i].second;
            connections_[new_idx].push_back(neighbor_idx);
            connections_[neighbor_idx].push_back(new_idx);
        }
    }
    
    size_t find_closest_unvisited(const Vector& query, 
                                 const std::vector<bool>& visited) {
        float best_dist = std::numeric_limits<float>::max();
        size_t best_idx = vectors_.size(); // 无效索引
        
        for (size_t i = 0; i < vectors_.size(); ++i) {
            if (!visited[i]) {
                float dist = query.distance(vectors_[i]);
                if (dist < best_dist) {
                    best_dist = dist;
                    best_idx = i;
                }
            }
        }
        
        return best_idx;
    }
};

// IVF 索引（简化版）
class IVFIndex : public Index {
public:
    explicit IVFIndex(size_t num_clusters = 8) 
        : num_clusters_(num_clusters) {}
    
    bool add_vector(const Vector& vector) override {
        vectors_.push_back(vector);
        
        // 如果需要，重新聚类
        if (vectors_.size() % 100 == 0) { // 每100个向量重新聚类一次
            rebuild_clusters();
        } else if (!cluster_centers_.empty()) {
            // 分配到最近的聚类
            size_t cluster_id = find_nearest_cluster(vector);
            clusters_[cluster_id].push_back(vectors_.size() - 1);
        }
        
        return true;
    }
    
    std::vector<SearchResult> search(const Vector& query, size_t k) override {
        if (vectors_.empty()) return {};
        
        if (cluster_centers_.empty()) {
            rebuild_clusters();
        }
        
        // 找到最近的几个聚类中心
        size_t num_clusters_to_search = std::min(static_cast<size_t>(3), 
                                                cluster_centers_.size());
        
        std::vector<std::pair<float, size_t>> cluster_distances;
        for (size_t i = 0; i < cluster_centers_.size(); ++i) {
            float dist = query.distance(cluster_centers_[i]);
            cluster_distances.emplace_back(dist, i);
        }
        
        std::sort(cluster_distances.begin(), cluster_distances.end());
        
        // 在选定的聚类中搜索
        std::vector<SearchResult> results;
        
        for (size_t i = 0; i < num_clusters_to_search; ++i) {
            size_t cluster_id = cluster_distances[i].second;
            
            for (size_t vec_idx : clusters_[cluster_id]) {
                float dist = query.distance(vectors_[vec_idx]);
                results.emplace_back(vectors_[vec_idx].id, dist);
            }
        }
        
        // 排序并返回top-k
        std::sort(results.begin(), results.end(),
                 [](const SearchResult& a, const SearchResult& b) {
                     return a.distance < b.distance;
                 });
        
        if (results.size() > k) {
            results.resize(k);
        }
        
        return results;
    }
    
    size_t size() const override { return vectors_.size(); }
    std::string get_type() const override { return "ivf"; }

private:
    size_t num_clusters_;
    std::vector<Vector> vectors_;
    std::vector<Vector> cluster_centers_;
    std::vector<std::vector<size_t>> clusters_;
    
    void rebuild_clusters() {
        if (vectors_.empty()) return;
        
        // 简化的k-means聚类
        cluster_centers_.clear();
        clusters_.clear();
        clusters_.resize(num_clusters_);
        
        // 随机初始化聚类中心
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, static_cast<int>(vectors_.size() - 1));
        
        for (size_t i = 0; i < num_clusters_; ++i) {
            size_t idx = static_cast<size_t>(dis(gen));
            cluster_centers_.push_back(vectors_[idx]);
        }
        
        // 分配向量到聚类
        for (size_t i = 0; i < vectors_.size(); ++i) {
            size_t cluster_id = find_nearest_cluster(vectors_[i]);
            clusters_[cluster_id].push_back(i);
        }
    }
    
    size_t find_nearest_cluster(const Vector& vector) {
        if (cluster_centers_.empty()) return 0;
        
        float best_dist = std::numeric_limits<float>::max();
        size_t best_cluster = 0;
        
        for (size_t i = 0; i < cluster_centers_.size(); ++i) {
            float dist = vector.distance(cluster_centers_[i]);
            if (dist < best_dist) {
                best_dist = dist;
                best_cluster = i;
            }
        }
        
        return best_cluster;
    }
};

} // namespace sage_flow

using namespace sage_flow;

// BruteForceIndex 测试套件
class BruteForceIndexTest : public ::testing::Test {
protected:
    void SetUp() override {
        index_ = std::make_unique<BruteForceIndex>();
        
        // 创建测试向量
        test_vectors_ = {
            Vector({1.0f, 0.0f}, "vec1"),
            Vector({0.0f, 1.0f}, "vec2"),
            Vector({1.0f, 1.0f}, "vec3"),
            Vector({0.5f, 0.5f}, "vec4")
        };
        
        // 添加到索引
        for (const auto& vec : test_vectors_) {
            index_->add_vector(vec);
        }
    }

    std::unique_ptr<BruteForceIndex> index_;
    std::vector<Vector> test_vectors_;
};

TEST_F(BruteForceIndexTest, BasicOperations) {
    EXPECT_EQ(index_->size(), 4);
    EXPECT_EQ(index_->get_type(), "brute_force");
}

TEST_F(BruteForceIndexTest, ExactSearch) {
    // 搜索完全匹配的向量
    Vector query({1.0f, 0.0f}, "query");
    auto results = index_->search(query, 1);
    
    EXPECT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].id, "vec1");
    EXPECT_NEAR(results[0].distance, 0.0f, 1e-6f);
}

TEST_F(BruteForceIndexTest, TopKSearch) {
    Vector query({0.0f, 0.0f}, "query");
    auto results = index_->search(query, 3);
    
    EXPECT_EQ(results.size(), 3);
    
    // 结果应该按距离排序
    for (size_t i = 0; i < results.size() - 1; ++i) {
        EXPECT_LE(results[i].distance, results[i + 1].distance);
    }
}

// HNSWIndex 测试套件
class HNSWIndexTest : public ::testing::Test {
protected:
    void SetUp() override {
        index_ = std::make_unique<HNSWIndex>(4); // 最大连接数为4
        
        // 创建更多测试向量
        for (int i = 0; i < 10; ++i) {
            float x = static_cast<float>(i) / 10.0f;
            float y = static_cast<float>(i % 3) / 3.0f;
            Vector vec({x, y}, "vec" + std::to_string(i));
            index_->add_vector(vec);
        }
    }

    std::unique_ptr<HNSWIndex> index_;
};

TEST_F(HNSWIndexTest, BasicOperations) {
    EXPECT_EQ(index_->size(), 10);
    EXPECT_EQ(index_->get_type(), "hnsw");
}

TEST_F(HNSWIndexTest, ApproximateSearch) {
    Vector query({0.5f, 0.5f}, "query");
    auto results = index_->search(query, 3);
    
    EXPECT_LE(results.size(), 3);
    EXPECT_GT(results.size(), 0);
    
    // 结果应该按距离排序
    for (size_t i = 0; i < results.size() - 1; ++i) {
        EXPECT_LE(results[i].distance, results[i + 1].distance);
    }
}

// IVFIndex 测试套件
class IVFIndexTest : public ::testing::Test {
protected:
    void SetUp() override {
        index_ = std::make_unique<IVFIndex>(3); // 3个聚类
        
        // 创建测试向量
        for (int i = 0; i < 20; ++i) {
            float x = static_cast<float>(i % 5) / 5.0f;
            float y = static_cast<float>(i / 5) / 4.0f;
            Vector vec({x, y}, "vec" + std::to_string(i));
            index_->add_vector(vec);
        }
    }

    std::unique_ptr<IVFIndex> index_;
};

TEST_F(IVFIndexTest, BasicOperations) {
    EXPECT_EQ(index_->size(), 20);
    EXPECT_EQ(index_->get_type(), "ivf");
}

TEST_F(IVFIndexTest, ClusteredSearch) {
    Vector query({0.2f, 0.2f}, "query");
    auto results = index_->search(query, 5);
    
    EXPECT_LE(results.size(), 5);
    EXPECT_GT(results.size(), 0);
    
    // 结果应该按距离排序
    for (size_t i = 0; i < results.size() - 1; ++i) {
        EXPECT_LE(results[i].distance, results[i + 1].distance);
    }
}

// 索引比较测试
class IndexComparisonTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建相同的测试数据
        for (int i = 0; i < 100; ++i) {
            float x = static_cast<float>(i % 10) / 10.0f;
            float y = static_cast<float>(i / 10) / 10.0f;
            Vector vec({x, y}, "vec" + std::to_string(i));
            test_vectors_.push_back(vec);
        }
        
        // 创建不同类型的索引
        brute_force_ = std::make_unique<BruteForceIndex>();
        hnsw_ = std::make_unique<HNSWIndex>();
        ivf_ = std::make_unique<IVFIndex>(5);
        
        // 添加相同的数据到所有索引
        for (const auto& vec : test_vectors_) {
            brute_force_->add_vector(vec);
            hnsw_->add_vector(vec);
            ivf_->add_vector(vec);
        }
    }

    std::vector<Vector> test_vectors_;
    std::unique_ptr<BruteForceIndex> brute_force_;
    std::unique_ptr<HNSWIndex> hnsw_;
    std::unique_ptr<IVFIndex> ivf_;
};

TEST_F(IndexComparisonTest, SameDataSize) {
    EXPECT_EQ(brute_force_->size(), test_vectors_.size());
    EXPECT_EQ(hnsw_->size(), test_vectors_.size());
    EXPECT_EQ(ivf_->size(), test_vectors_.size());
}

TEST_F(IndexComparisonTest, SearchQuality) {
    Vector query({0.55f, 0.55f}, "query");
    const size_t k = 5;
    
    auto bf_results = brute_force_->search(query, k);
    auto hnsw_results = hnsw_->search(query, k);
    auto ivf_results = ivf_->search(query, k);
    
    // 所有索引都应该返回结果
    EXPECT_EQ(bf_results.size(), k);
    EXPECT_GT(hnsw_results.size(), 0);
    EXPECT_GT(ivf_results.size(), 0);
    
    // 暴力搜索的结果应该是最准确的
    // 其他索引的第一个结果应该与暴力搜索的第一个结果相近
    if (!hnsw_results.empty()) {
        float bf_best_dist = bf_results[0].distance;
        float hnsw_best_dist = hnsw_results[0].distance;
        
        // HNSW的最佳结果不应该比暴力搜索差太多
        EXPECT_LT(hnsw_best_dist, bf_best_dist * 2.0f);
    }
}

// 性能测试
class IndexPerformanceTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建大量测试数据
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> dis(0.0f, 1.0f);
        
        large_dataset_.reserve(1000);
        for (int i = 0; i < 1000; ++i) {
            Vector vec({dis(gen), dis(gen), dis(gen)}, "vec" + std::to_string(i));
            large_dataset_.push_back(vec);
        }
    }

    std::vector<Vector> large_dataset_;
};

TEST_F(IndexPerformanceTest, IndexBuildingPerformance) {
    auto brute_force = std::make_unique<BruteForceIndex>();
    auto hnsw = std::make_unique<HNSWIndex>();
    auto ivf = std::make_unique<IVFIndex>(10);
    
    // 测试暴力索引构建时间
    auto start = std::chrono::high_resolution_clock::now();
    for (const auto& vec : large_dataset_) {
        brute_force->add_vector(vec);
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto bf_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 测试HNSW索引构建时间
    start = std::chrono::high_resolution_clock::now();
    for (const auto& vec : large_dataset_) {
        hnsw->add_vector(vec);
    }
    end = std::chrono::high_resolution_clock::now();
    auto hnsw_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 测试IVF索引构建时间
    start = std::chrono::high_resolution_clock::now();
    for (const auto& vec : large_dataset_) {
        ivf->add_vector(vec);
    }
    end = std::chrono::high_resolution_clock::now();
    auto ivf_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 性能基准：1000个向量的索引构建应该在合理时间内完成
    EXPECT_LT(bf_duration.count(), 1000);   // 1秒
    EXPECT_LT(hnsw_duration.count(), 2000); // 2秒
    EXPECT_LT(ivf_duration.count(), 1500);  // 1.5秒
    
    // 验证所有索引都成功构建
    EXPECT_EQ(brute_force->size(), large_dataset_.size());
    EXPECT_EQ(hnsw->size(), large_dataset_.size());
    EXPECT_EQ(ivf->size(), large_dataset_.size());
}

TEST_F(IndexPerformanceTest, SearchPerformance) {
    // 构建索引
    auto brute_force = std::make_unique<BruteForceIndex>();
    auto hnsw = std::make_unique<HNSWIndex>();
    
    for (const auto& vec : large_dataset_) {
        brute_force->add_vector(vec);
        hnsw->add_vector(vec);
    }
    
    Vector query({0.5f, 0.5f, 0.5f}, "query");
    const size_t k = 10;
    const int num_queries = 100;
    
    // 测试暴力搜索性能
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < num_queries; ++i) {
        auto results = brute_force->search(query, k);
        EXPECT_EQ(results.size(), k);
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto bf_search_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // 测试HNSW搜索性能
    start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < num_queries; ++i) {
        auto results = hnsw->search(query, k);
        EXPECT_GT(results.size(), 0);
    }
    end = std::chrono::high_resolution_clock::now();
    auto hnsw_search_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // HNSW搜索应该比暴力搜索更快
    EXPECT_LT(hnsw_search_duration.count(), bf_search_duration.count());
    
    // 基本性能要求
    EXPECT_LT(bf_search_duration.count(), 5000);   // 5秒内完成100次暴力搜索
    EXPECT_LT(hnsw_search_duration.count(), 1000); // 1秒内完成100次HNSW搜索
}

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}