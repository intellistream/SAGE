
#include "index/hnsw.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <ranges>
#include <unordered_set>

namespace sage_flow {


auto HNSW::AddVector(uint64_t id, const std::vector<float>& vector) -> bool {
  if (vectors_.find(id) != vectors_.end()) {
    return false;  // Vector already exists
  }

  vectors_[id] = vector;

  int level = get_random_level();
  Node node{id, level,
            std::vector<std::vector<uint64_t>>(static_cast<size_t>(level + 1))};

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
    auto selected =
        select_neighbors_simple(vector, candidates, max_connections);

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

  // Remove connections from neighbors
  for (int lc = 0; lc <= node_it->second.level_; ++lc) {
    for (auto neighbor_id : node_it->second.links_[lc]) {
      auto& neighbor_links = nodes_[neighbor_id].links_[lc];
      neighbor_links.erase(std::remove(neighbor_links.begin(), neighbor_links.end(), id), neighbor_links.end());
    }
  }

  // Remove vector and node
  vectors_.erase(id);
  nodes_.erase(id);
  return true;
}

auto HNSW::Search(const std::vector<float>& query_vector,
                  size_t k) const -> std::vector<SearchResult> {
  std::vector<SearchResult> results;
  if (nodes_.empty()) {
    return results;
  }

  // Simplified search - find k nearest vectors
  std::priority_queue<Neighbor> candidates;
  search_layer(query_vector, candidates, max_level_, ef_search_);

  while (candidates.size() > k) {
    candidates.pop();
  }

  while (!candidates.empty()) {
    auto neighbor = candidates.top();
    candidates.pop();
    results.emplace_back(neighbor.id_, neighbor.dist_);
  }

  std::reverse(results.begin(), results.end());
  return results;
}

auto HNSW::Build() -> bool {
  // HNSW is built incrementally, no separate build step needed
  return true;
}

auto HNSW::SaveIndex(const std::string& file_path) const -> bool {
  std::ofstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }

  // Simple serialization - save parameters and nodes
  file.write(reinterpret_cast<const char*>(&m_), sizeof(m_));
  file.write(reinterpret_cast<const char*>(&ef_construction_), sizeof(ef_construction_));
  file.write(reinterpret_cast<const char*>(&ef_search_), sizeof(ef_search_));
  file.write(reinterpret_cast<const char*>(&max_level_), sizeof(max_level_));
  file.write(reinterpret_cast<const char*>(&entry_point_), sizeof(entry_point_));

  // Save vectors and nodes
  size_t num_vectors = vectors_.size();
  file.write(reinterpret_cast<const char*>(&num_vectors), sizeof(num_vectors));
  for (const auto& [id, vector] : vectors_) {
    file.write(reinterpret_cast<const char*>(&id), sizeof(id));
    size_t vec_size = vector.size();
    file.write(reinterpret_cast<const char*>(&vec_size), sizeof(vec_size));
    file.write(reinterpret_cast<const char*>(vector.data()), vec_size * sizeof(float));
  }

  // Save nodes
  size_t num_nodes = nodes_.size();
  file.write(reinterpret_cast<const char*>(&num_nodes), sizeof(num_nodes));
  for (const auto& [id, node] : nodes_) {
    file.write(reinterpret_cast<const char*>(&id), sizeof(id));
    file.write(reinterpret_cast<const char*>(&node.level_), sizeof(node.level_));
    for (const auto& level_links : node.links_) {
      size_t link_size = level_links.size();
      file.write(reinterpret_cast<const char*>(&link_size), sizeof(link_size));
      for (auto link_id : level_links) {
        file.write(reinterpret_cast<const char*>(&link_id), sizeof(link_id));
      }
    }
  }

  return true;
}

auto HNSW::LoadIndex(const std::string& file_path) -> bool {
  std::ifstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }

  // Load parameters
  file.read(reinterpret_cast<char*>(&m_), sizeof(m_));
  file.read(reinterpret_cast<char*>(&ef_construction_), sizeof(ef_construction_));
  file.read(reinterpret_cast<char*>(&ef_search_), sizeof(ef_search_));
  file.read(reinterpret_cast<char*>(&max_level_), sizeof(max_level_));
  file.read(reinterpret_cast<char*>(&entry_point_), sizeof(entry_point_));

  // Load vectors
  size_t num_vectors;
  file.read(reinterpret_cast<char*>(&num_vectors), sizeof(num_vectors));
  for (size_t i = 0; i < num_vectors; ++i) {
    uint64_t id;
    file.read(reinterpret_cast<char*>(&id), sizeof(id));
    size_t vec_size;
    file.read(reinterpret_cast<char*>(&vec_size), sizeof(vec_size));
    std::vector<float> vector(vec_size);
    file.read(reinterpret_cast<char*>(vector.data()), vec_size * sizeof(float));
    vectors_[id] = std::move(vector);
  }

  // Load nodes
  size_t num_nodes;
  file.read(reinterpret_cast<char*>(&num_nodes), sizeof(num_nodes));
  for (size_t i = 0; i < num_nodes; ++i) {
    uint64_t id;
    file.read(reinterpret_cast<char*>(&id), sizeof(id));
    int level;
    file.read(reinterpret_cast<char*>(&level), sizeof(level));
    Node node{id, level, std::vector<std::vector<uint64_t>>(static_cast<size_t>(level + 1))};
    for (int lc = 0; lc <= level; ++lc) {
      size_t link_size;
      file.read(reinterpret_cast<char*>(&link_size), sizeof(link_size));
      for (size_t j = 0; j < link_size; ++j) {
        uint64_t link_id;
        file.read(reinterpret_cast<char*>(&link_id), sizeof(link_id));
        node.links_[lc].push_back(link_id);
      }
    }
    nodes_[id] = std::move(node);
  }

  return true;
}

void HNSW::Clear() {
  vectors_.clear();
  nodes_.clear();
  max_level_ = -1;
  entry_point_ = std::numeric_limits<uint64_t>::max();
}

auto HNSW::Size() const -> size_t {
  return vectors_.size();
}

auto HNSW::GetType() const -> IndexType {
  return IndexType::kHnsw;
}

float HNSW::l2_distance(const std::vector<float>& a,
                        const std::vector<float>& b) const {
  float dist = 0.0f;
  for (size_t i = 0; i < a.size(); ++i) {
    float diff = a[i] - b[i];
    dist += diff * diff;
  }
  return std::sqrt(dist);
}

void HNSW::search_layer(const std::vector<float>& query,
                        std::priority_queue<Neighbor>& candidates, int layer,
                        int ef) const {
  if (layer > max_level_) {
    return;
  }

  // Simplified search at this layer
  for (const auto& [node_id, node_data] : nodes_) {
    if (static_cast<size_t>(layer) < node_data.links_.size()) {
      float dist = l2_distance(query, vectors_.at(node_id));
      if (candidates.size() < static_cast<size_t>(ef)) {
        candidates.push({node_id, dist});
      } else if (dist < candidates.top().dist_) {
        candidates.pop();
        candidates.push({node_id, dist});
      }
    }
  }
}

auto HNSW::select_neighbors_heuristic(
    const std::vector<float>& query, const std::vector<uint64_t>& candidates,
    int m, int layer, bool extend_candidates,
    bool keep_pruned) const -> std::vector<uint64_t> {
  // Simplified heuristic selection
  std::vector<uint64_t> selected;
  std::priority_queue<Neighbor> pq;

  for (auto id : candidates) {
    if (vectors_.count(id)) {
      float dist = l2_distance(query, vectors_.at(id));
      pq.push({id, dist});
    }
  }

  while (!pq.empty() && selected.size() < static_cast<size_t>(m)) {
    selected.push_back(pq.top().id_);
    pq.pop();
  }

  return selected;
}

auto HNSW::select_neighbors_simple(const std::vector<float>& query,
                                   const std::vector<uint64_t>& candidates,
                                   int m) const -> std::vector<uint64_t> {
  std::vector<uint64_t> selected;
  std::priority_queue<Neighbor> pq;

  for (auto id : candidates) {
    if (vectors_.count(id)) {
      float dist = l2_distance(query, vectors_.at(id));
      pq.push({id, dist});
    }
  }

  while (!pq.empty() && selected.size() < static_cast<size_t>(m)) {
    selected.push_back(pq.top().id_);
    pq.pop();
  }

  return selected;
}

}  // namespace sage_flow