#pragma once

#include <numbers>
#include <queue>
#include <random>
#include <unordered_map>
#include <vector>

#include "index.h"

namespace sage_flow {

/**
 * @brief HNSW (Hierarchical Navigable Small World) index implementation
 * Ported from DynaGraph/include/index/hnsw.h
 */
class HNSW final : public Index {
 public:
  explicit HNSW(std::shared_ptr<MemoryPool> memory_pool, 
                int m = 20, int ef_construction = 100, int ef_search = 40);

  ~HNSW() override = default;

  // Prevent copying
  HNSW(const HNSW&) = delete;
  auto operator=(const HNSW&) -> HNSW& = delete;

  // Allow moving
  HNSW(HNSW&&) = default;
  auto operator=(HNSW&&) -> HNSW& = default;

  // Index interface implementation
  auto Initialize(const IndexConfig& config) -> bool override;
  auto AddVector(uint64_t id, const std::vector<float>& vector) -> bool override;
  auto RemoveVector(uint64_t id) -> bool override;
  auto Search(const std::vector<float>& query_vector, size_t k) const -> std::vector<SearchResult> override;
  auto Build() -> bool override;
  auto SaveIndex(const std::string& file_path) const -> bool override;
  auto LoadIndex(const std::string& file_path) -> bool override;
  auto Size() const -> size_t override;
  void Clear() override;
  auto GetType() const -> IndexType override;

 private:
  struct Neighbor {
    uint64_t id_;
    float dist_;

    auto operator<(const Neighbor& other) const -> bool { return dist_ < other.dist_; }
    auto operator>(const Neighbor& other) const -> bool { return dist_ > other.dist_; }
  };

  struct Node {
    uint64_t id_;
    int level_;
    std::vector<std::vector<uint64_t>> links_;  // links[l] = neighbors at level l
  };

  // HNSW parameters
  int m_;                // Max connections per layer (except top layer)
  int ef_construction_;  // Size of dynamic candidate list during construction
  int ef_search_;        // Size of dynamic candidate list during search
  float ml_{std::numbers::log2e_v<float>};    // Level generation factor (1/ln(2))

  // Index state
  int max_level_{-1};
  uint64_t entry_point_;
  std::unordered_map<uint64_t, Node> nodes_;
  std::unordered_map<uint64_t, std::vector<float>> vectors_;  // Store vectors
  mutable std::mt19937 rng_;

  // Helper methods
  auto l2_distance(const std::vector<float>& a, const std::vector<float>& b) const -> float;
  auto get_random_level() -> int;
  void search_layer(const std::vector<float>& query, 
                   std::priority_queue<Neighbor>& candidates, 
                   int layer, int ef) const;
  auto select_neighbors_heuristic(const std::vector<float>& query,
                                 const std::vector<uint64_t>& candidates,
                                 int m, int layer, bool extend_candidates,
                                 bool keep_pruned) const -> std::vector<uint64_t>;
  auto select_neighbors_simple(const std::vector<float>& query,
                              const std::vector<uint64_t>& candidates,
                              int m) const -> std::vector<uint64_t>;
};

}  // namespace sage_flow
