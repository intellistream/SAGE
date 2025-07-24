#include "index/hnsw.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <unordered_set>

namespace sage_flow {

HNSW::HNSW(std::shared_ptr<MemoryPool> memory_pool, int m, int ef_construction, int ef_search)
    : Index(std::move(memory_pool)),
      m_(m),
      ef_construction_(ef_construction),
      ef_search_(ef_search),
      ml_(1.0f / std::log(2.0f)),
      max_level_(-1),
      entry_point_(std::numeric_limits<uint64_t>::max()),
      rng_(std::random_device{}()) {}

auto HNSW::Initialize(const IndexConfig& config) -> bool {
  // Update parameters from config if needed
  if (config.hnsw_m_ > 0) {
    m_ = static_cast<int>(config.hnsw_m_);
  }
  if (config.hnsw_ef_construction_ > 0) {
    ef_construction_ = static_cast<int>(config.hnsw_ef_construction_);
  }
  if (config.hnsw_ef_search_ > 0) {
    ef_search_ = static_cast<int>(config.hnsw_ef_search_);
  }
  
  Clear();
  return true;
}

auto HNSW::AddVector(uint64_t id, const std::vector<float>& vector) -> bool {
  if (vectors_.find(id) != vectors_.end()) {
    return false;  // Vector already exists
  }

  vectors_[id] = vector;
  
  int level = get_random_level();
  Node node{id, level, std::vector<std::vector<uint64_t>>(static_cast<size_t>(level + 1))};
  
  if (nodes_.empty()) {
    // First node becomes entry point
    entry_point_ = id;
    max_level_ = level;
    nodes_[id] = std::move(node);
    return true;
  }

  // Simplified insertion - just connect to nearest neighbors at each level
  for (int lc = 0; lc <= level; lc++) {
    // Find nearest neighbors at this level
    std::vector<uint64_t> candidates;
    for (const auto& [node_id, node_data] : nodes_) {
      if (static_cast<size_t>(lc) < node_data.links_.size()) {
        candidates.push_back(node_id);
      }
    }
    
    // Connect to closest neighbors
    int max_connections = (lc == 0) ? 2 * m_ : m_;
    auto selected = select_neighbors_simple(vector, candidates, max_connections);
    
    for (auto neighbor_id : selected) {
      node.links_[static_cast<size_t>(lc)].push_back(neighbor_id);
      nodes_[neighbor_id].links_[static_cast<size_t>(lc)].push_back(id);
    }
  }
  
  nodes_[id] = std::move(node);
  
  // Update entry point if new node is at higher level
  if (level > max_level_) {
    max_level_ = level;
    entry_point_ = id;
  }
  
  return true;
}

auto HNSW::RemoveVector(uint64_t id) -> bool {
  auto node_it = nodes_.find(id);
  if (node_it == nodes_.end()) {
    return false;  // Vector doesn't exist
  }
  
  // Remove all connections to this node
  for (size_t level = 0; level < node_it->second.links_.size(); level++) {
    for (auto neighbor_id : node_it->second.links_[level]) {
      auto& neighbor_links = nodes_[neighbor_id].links_[level];
      neighbor_links.erase(std::remove(neighbor_links.begin(), neighbor_links.end(), id), neighbor_links.end());
    }
  }
  
  // Remove from data structures
  nodes_.erase(node_it);
  vectors_.erase(id);
  
  // Update entry point if needed
  if (entry_point_ == id) {
    if (nodes_.empty()) {
      entry_point_ = std::numeric_limits<uint64_t>::max();
      max_level_ = -1;
    } else {
      // Find new entry point with highest level
      max_level_ = -1;
      for (const auto& [node_id, node] : nodes_) {
        if (node.level_ > max_level_) {
          max_level_ = node.level_;
          entry_point_ = node_id;
        }
      }
    }
  }
  
  return true;
}

auto HNSW::Search(const std::vector<float>& query_vector, size_t k) const -> std::vector<SearchResult> {
  if (nodes_.empty() || k == 0) {
    return {};
  }
  
  // Simple greedy search for now
  std::vector<Neighbor> candidates;
  for (const auto& [id, vector] : vectors_) {
    float dist = l2_distance(query_vector, vector);
    candidates.push_back({id, dist});
  }
  
  // Sort by distance and return top k
  std::sort(candidates.begin(), candidates.end());
  
  std::vector<SearchResult> results;
  size_t result_count = std::min(k, candidates.size());
  for (size_t i = 0; i < result_count; i++) {
    results.emplace_back(candidates[i].id_, candidates[i].dist_);
  }
  
  return results;
}

auto HNSW::Build() -> bool {
  // HNSW builds incrementally, no separate build step needed
  return true;
}

auto HNSW::SaveIndex(const std::string& file_path) const -> bool {
  std::ofstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }
  
  // Save basic parameters
  file.write(reinterpret_cast<const char*>(&m_), sizeof(m_));
  file.write(reinterpret_cast<const char*>(&ef_construction_), sizeof(ef_construction_));
  file.write(reinterpret_cast<const char*>(&ef_search_), sizeof(ef_search_));
  file.write(reinterpret_cast<const char*>(&max_level_), sizeof(max_level_));
  file.write(reinterpret_cast<const char*>(&entry_point_), sizeof(entry_point_));
  
  // Save vectors
  size_t vector_count = vectors_.size();
  file.write(reinterpret_cast<const char*>(&vector_count), sizeof(vector_count));
  
  for (const auto& [id, vector] : vectors_) {
    file.write(reinterpret_cast<const char*>(&id), sizeof(id));
    size_t dim = vector.size();
    file.write(reinterpret_cast<const char*>(&dim), sizeof(dim));
    file.write(reinterpret_cast<const char*>(vector.data()), static_cast<std::streamsize>(dim * sizeof(float)));
  }
  
  return file.good();
}

auto HNSW::LoadIndex(const std::string& file_path) -> bool {
  std::ifstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }
  
  Clear();
  
  // Load basic parameters
  file.read(reinterpret_cast<char*>(&m_), sizeof(m_));
  file.read(reinterpret_cast<char*>(&ef_construction_), sizeof(ef_construction_));
  file.read(reinterpret_cast<char*>(&ef_search_), sizeof(ef_search_));
  file.read(reinterpret_cast<char*>(&max_level_), sizeof(max_level_));
  file.read(reinterpret_cast<char*>(&entry_point_), sizeof(entry_point_));
  
  // Load vectors
  size_t vector_count;
  file.read(reinterpret_cast<char*>(&vector_count), sizeof(vector_count));
  
  for (size_t i = 0; i < vector_count; i++) {
    uint64_t id;
    file.read(reinterpret_cast<char*>(&id), sizeof(id));
    
    size_t dim;
    file.read(reinterpret_cast<char*>(&dim), sizeof(dim));
    
    std::vector<float> vector(dim);
    file.read(reinterpret_cast<char*>(vector.data()), static_cast<std::streamsize>(dim * sizeof(float)));
    
    vectors_[id] = std::move(vector);
  }
  
  return file.good();
}

auto HNSW::Size() const -> size_t {
  return vectors_.size();
}

void HNSW::Clear() {
  nodes_.clear();
  vectors_.clear();
  max_level_ = -1;
  entry_point_ = std::numeric_limits<uint64_t>::max();
}

auto HNSW::GetType() const -> IndexType {
  return IndexType::kHnsw;
}

// Private helper methods
auto HNSW::l2_distance(const std::vector<float>& a, const std::vector<float>& b) const -> float {
  float dist = 0.0f;
  for (size_t i = 0; i < a.size(); i++) {
    float diff = a[i] - b[i];
    dist += diff * diff;
  }
  return std::sqrt(dist);
}

auto HNSW::get_random_level() -> int {
  int level = 0;
  std::uniform_real_distribution<float> dis(0.0f, 1.0f);
  while (dis(rng_) < ml_ && level < 16) {  // Cap at reasonable level
    level++;
  }
  return level;
}

auto HNSW::select_neighbors_simple(const std::vector<float>& query,
                                  const std::vector<uint64_t>& candidates,
                                  int m) const -> std::vector<uint64_t> {
  std::vector<Neighbor> neighbors;
  for (auto id : candidates) {
    auto it = vectors_.find(id);
    if (it != vectors_.end()) {
      float dist = l2_distance(query, it->second);
      neighbors.push_back({id, dist});
    }
  }
  
  std::sort(neighbors.begin(), neighbors.end());
  
  std::vector<uint64_t> result;
  for (int i = 0; i < std::min(m, static_cast<int>(neighbors.size())); i++) {
    result.push_back(neighbors[static_cast<size_t>(i)].id_);
  }
  
  return result;
}

// Placeholder implementations for methods not used in simplified version
void HNSW::search_layer(const std::vector<float>& query,
                       std::priority_queue<Neighbor>& candidates,
                       int layer, int ef) const {
  // Placeholder - not implemented in simplified version
  (void)query;
  (void)candidates;
  (void)layer;
  (void)ef;
}

auto HNSW::select_neighbors_heuristic(const std::vector<float>& query,
                                     const std::vector<uint64_t>& candidates,
                                     int m, int layer, bool extend_candidates,
                                     bool keep_pruned) const -> std::vector<uint64_t> {
  // Use simple selection for now
  (void)layer;
  (void)extend_candidates;
  (void)keep_pruned;
  return select_neighbors_simple(query, candidates, m);
}

}  // namespace sage_flow
