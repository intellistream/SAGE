#pragma once

#include <unordered_map>
#include <vector>

#include "index.h"

namespace sage_flow {

/**
 * @brief IVF (Inverted File) index implementation
 * Ported from DynaGraph/include/index/ivf.h
 * 
 * IVF index divides the vector space into clusters using k-means,
 * then maintains inverted lists for each cluster. During search,
 * only a subset of clusters are searched (nprobe clusters).
 */
class IVF final : public Index {
 public:
  explicit IVF(std::shared_ptr<MemoryPool> memory_pool,
               int num_clusters = 100, double rebuild_threshold = 0.5, int nprobe = 10);

  ~IVF() override = default;

  // Prevent copying
  IVF(const IVF&) = delete;
  auto operator=(const IVF&) -> IVF& = delete;

  // Allow moving
  IVF(IVF&&) = default;
  auto operator=(IVF&&) -> IVF& = default;

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
  // IVF parameters
  int num_clusters_;                    // Number of clusters for k-means
  double rebuild_threshold_;            // Threshold to trigger rebuilding (as ratio)
  int nprobe_;                         // Number of clusters to search
  
  // Index state
  std::vector<std::vector<float>> centroids_;                          // Cluster centroids
  std::unordered_map<int, std::vector<uint64_t>> inverted_lists_;     // Cluster -> vector IDs
  std::unordered_map<uint64_t, std::vector<float>> vectors_;          // Store all vectors
  std::unordered_map<uint64_t, int> vector_to_cluster_;               // Vector ID -> cluster ID
  int vectors_since_last_rebuild_{0};                                  // Counter for rebuild trigger
  
  // Helper methods
  auto l2_distance(const std::vector<float>& a, const std::vector<float>& b) const -> float;
  auto assign_to_cluster(const std::vector<float>& vector) const -> int;
  void rebuild_clusters();
  void kmeans_clustering();
  auto search_clusters(const std::vector<float>& query_vector, int nprobe) const -> std::vector<int>;
};

}  // namespace sage_flow
