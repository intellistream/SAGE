#include "sage_db/anns/anns_interface.h"
#include "sage_db/anns/vamana/vertex.h"
#include "sage_db/anns/vamana/distance.h"

#include <algorithm>
#include <fstream>
#include <future>
#include <memory>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <stdexcept>

namespace sage_db {
namespace anns {

/**
 * @brief Vamana graph-based ANN algorithm
 *
 * Implementation of the Vamana algorithm from DiskANN paper.
 * Features:
 * - Greedy search with beam width control (efSearch)
 * - Robust pruning for graph quality
 * - Incremental insertion and deletion support
 * - Lazy deletion with batch compaction
 */
class VamanaANNS : public ANNSAlgorithm {
 public:
  VamanaANNS() = default;
  ~VamanaANNS() override = default;

  std::string name() const override { return "Vamana"; }

  bool supports_updates() const override { return true; }
  bool supports_deletions() const override { return true; }

  void fit(const std::vector<VectorId>& ids,
           const std::vector<Vector>& vectors,
           const AlgorithmParams& params) override;

  std::vector<ANNSResult> query(const std::vector<Vector>& queries,
                                 idx_t k,
                                 const AlgorithmParams& params) override;

  void add_vector(VectorId id, const Vector& vector) override;

  void add_vectors(const std::vector<VectorId>& ids,
                   const std::vector<Vector>& vectors) override;

  void delete_vector(VectorId id) override;

  void delete_vectors(const std::vector<VectorId>& ids) override;

  idx_t get_index_size() const override;

  size_t get_memory_usage() const override;

  void save(const std::string& path) const override;

  void load(const std::string& path) override;

 private:
  struct DistAndId {
    float dist;
    idx_t id;

    DistAndId(float d, idx_t i) : dist(d), id(i) {}

    bool operator<(const DistAndId& other) const { return dist < other.dist; }
    bool operator>(const DistAndId& other) const { return dist > other.dist; }
    bool operator==(const DistAndId& other) const { return id == other.id; }
  };

  struct CompByDistLess {
    bool operator()(const DistAndId& a, const DistAndId& b) const {
      return a.dist < b.dist;
    }
  };

  struct CompByDistGreater {
    bool operator()(const DistAndId& a, const DistAndId& b) const {
      return a.dist > b.dist;
    }
  };

  // Max-heap: top element has largest distance
  using MaxHeap = std::priority_queue<DistAndId, std::vector<DistAndId>, CompByDistLess>;
  // Min-heap: top element has smallest distance
  using MinHeap = std::priority_queue<DistAndId, std::vector<DistAndId>, CompByDistGreater>;

  // Core algorithm parameters
  idx_t M_ = 16;              ///< Degree bound during construction
  idx_t Mmax_ = 32;           ///< Maximum degree for vertices
  idx_t ef_construction_ = 50;  ///< Beam width during construction
  idx_t ef_search_ = 200;     ///< Beam width during search
  float alpha_ = 1.2f;        ///< Robust pruning parameter
  DistanceMetric metric_ = DistanceMetric::L2;

  // Graph state
  std::unordered_map<idx_t, vamana::VertexPtr> index_;  ///< Internal ID -> Vertex
  std::unordered_set<idx_t> delete_list_;  ///< Lazy deletion marker
  idx_t entry_point_ = -1;    ///< Graph entry point
  idx_t next_internal_id_ = 0;  ///< Next internal vertex ID

  // ID mapping: external VectorId <-> internal idx_t
  std::unordered_map<VectorId, idx_t> id_map_;  ///< External -> Internal
  std::unordered_map<idx_t, VectorId> reverse_id_map_;  ///< Internal -> External

  idx_t dimension_ = 0;       ///< Vector dimension
  idx_t size_ = 0;            ///< Active vector count (excluding deleted)

  // Helper methods
  float compute_distance(const Vector& a, const Vector& b) const;

  void insert_vertex(idx_t internal_id, const Vector& vector);
  void add_links_starting_from(idx_t start_id, idx_t nearest_id, float d_nearest);
  void add_link(idx_t src, idx_t dest);

  void greedy_search(idx_t start, const Vector& query, MaxHeap& results, idx_t k) const;
  MaxHeap search_base_layer(idx_t entry, const Vector& query, idx_t ef) const;
  void greedy_update_nearest(idx_t& nearest, float& d_nearest, const Vector& query) const;

  void robust_prune(idx_t pivot, std::unordered_map<idx_t, float>& candidates,
                    float alpha, idx_t max_degree);
  void shrink_neighbor_list(MaxHeap& results, idx_t max_size);
  void shrink_neighbor_list_robust(MinHeap& input, std::vector<DistAndId>& output,
                                   idx_t max_size);

  void delete_vertex_internal(idx_t internal_id);
  void delete_batch_compact();

  ANNSResult search_single(const Vector& query, idx_t k) const;
};

}  // namespace anns
}  // namespace sage_db
