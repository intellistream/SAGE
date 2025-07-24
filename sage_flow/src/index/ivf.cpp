#include "index/ivf.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <random>
#include <unordered_set>

namespace sage_flow {

IVF::IVF(std::shared_ptr<MemoryPool> memory_pool, int num_clusters, double rebuild_threshold, int nprobe)
    : Index(std::move(memory_pool)),
      num_clusters_(num_clusters),
      rebuild_threshold_(rebuild_threshold),
      nprobe_(nprobe) {}

auto IVF::Initialize(const IndexConfig& config) -> bool {
  // Update parameters from config if needed
  if (config.ivf_nlist_ > 0) {
    num_clusters_ = static_cast<int>(config.ivf_nlist_);
  }
  if (config.ivf_nprobe_ > 0) {
    nprobe_ = static_cast<int>(config.ivf_nprobe_);
  }
  
  Clear();
  return true;
}

auto IVF::AddVector(uint64_t id, const std::vector<float>& vector) -> bool {
  if (vectors_.find(id) != vectors_.end()) {
    return false;  // Vector already exists
  }

  vectors_[id] = vector;
  vectors_since_last_rebuild_++;
  
  // If we have centroids, assign to cluster
  if (!centroids_.empty()) {
    int cluster_id = assign_to_cluster(vector);
    if (cluster_id >= 0) {
      inverted_lists_[cluster_id].push_back(id);
      vector_to_cluster_[id] = cluster_id;
    }
  }
  
  // Check if we need to rebuild clusters
  double growth_ratio = static_cast<double>(vectors_since_last_rebuild_) / static_cast<double>(vectors_.size());
  if (growth_ratio > rebuild_threshold_ && vectors_.size() >= static_cast<size_t>(num_clusters_)) {
    rebuild_clusters();
    vectors_since_last_rebuild_ = 0;
  }
  
  return true;
}

auto IVF::RemoveVector(uint64_t id) -> bool {
  auto vector_it = vectors_.find(id);
  if (vector_it == vectors_.end()) {
    return false;  // Vector doesn't exist
  }
  
  // Remove from cluster if assigned
  auto cluster_it = vector_to_cluster_.find(id);
  if (cluster_it != vector_to_cluster_.end()) {
    int cluster_id = cluster_it->second;
    auto& cluster_list = inverted_lists_[cluster_id];
    cluster_list.erase(std::remove(cluster_list.begin(), cluster_list.end(), id), cluster_list.end());
    vector_to_cluster_.erase(cluster_it);
  }
  
  // Remove from vectors
  vectors_.erase(vector_it);
  
  return true;
}

auto IVF::Search(const std::vector<float>& query_vector, size_t k) const -> std::vector<SearchResult> {
  if (vectors_.empty() || k == 0) {
    return {};
  }
  
  std::vector<SearchResult> results;
  
  if (centroids_.empty()) {
    // No clusters built yet, use brute force
    for (const auto& [id, vector] : vectors_) {
      float dist = l2_distance(query_vector, vector);
      results.emplace_back(id, dist);
    }
  } else {
    // Search in selected clusters
    auto cluster_ids = search_clusters(query_vector, nprobe_);
    
    for (int cluster_id : cluster_ids) {
      auto cluster_it = inverted_lists_.find(cluster_id);
      if (cluster_it != inverted_lists_.end()) {
        for (uint64_t vector_id : cluster_it->second) {
          auto vector_it = vectors_.find(vector_id);
          if (vector_it != vectors_.end()) {
            float dist = l2_distance(query_vector, vector_it->second);
            results.emplace_back(vector_id, dist);
          }
        }
      }
    }
  }
  
  // Sort by distance and return top k
  std::sort(results.begin(), results.end(), 
            [](const SearchResult& a, const SearchResult& b) {
              return a.distance_ < b.distance_;
            });
  
  if (results.size() > k) {
    results.resize(k);
  }
  
  return results;
}

auto IVF::Build() -> bool {
  if (vectors_.size() >= static_cast<size_t>(num_clusters_)) {
    rebuild_clusters();
    vectors_since_last_rebuild_ = 0;
  }
  return true;
}

auto IVF::SaveIndex(const std::string& file_path) const -> bool {
  std::ofstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }
  
  // Save parameters
  file.write(reinterpret_cast<const char*>(&num_clusters_), sizeof(num_clusters_));
  file.write(reinterpret_cast<const char*>(&rebuild_threshold_), sizeof(rebuild_threshold_));
  file.write(reinterpret_cast<const char*>(&nprobe_), sizeof(nprobe_));
  file.write(reinterpret_cast<const char*>(&vectors_since_last_rebuild_), sizeof(vectors_since_last_rebuild_));
  
  // Save vectors
  size_t vector_count = vectors_.size();
  file.write(reinterpret_cast<const char*>(&vector_count), sizeof(vector_count));
  
  for (const auto& [id, vector] : vectors_) {
    file.write(reinterpret_cast<const char*>(&id), sizeof(id));
    size_t dim = vector.size();
    file.write(reinterpret_cast<const char*>(&dim), sizeof(dim));
    file.write(reinterpret_cast<const char*>(vector.data()), static_cast<std::streamsize>(dim * sizeof(float)));
  }
  
  // Save centroids
  size_t centroid_count = centroids_.size();
  file.write(reinterpret_cast<const char*>(&centroid_count), sizeof(centroid_count));
  
  for (const auto& centroid : centroids_) {
    size_t dim = centroid.size();
    file.write(reinterpret_cast<const char*>(&dim), sizeof(dim));
    file.write(reinterpret_cast<const char*>(centroid.data()), static_cast<std::streamsize>(dim * sizeof(float)));
  }
  
  // Save inverted lists
  size_t list_count = inverted_lists_.size();
  file.write(reinterpret_cast<const char*>(&list_count), sizeof(list_count));
  
  for (const auto& [cluster_id, vector_ids] : inverted_lists_) {
    file.write(reinterpret_cast<const char*>(&cluster_id), sizeof(cluster_id));
    size_t id_count = vector_ids.size();
    file.write(reinterpret_cast<const char*>(&id_count), sizeof(id_count));
    file.write(reinterpret_cast<const char*>(vector_ids.data()), static_cast<std::streamsize>(id_count * sizeof(uint64_t)));
  }
  
  return file.good();
}

auto IVF::LoadIndex(const std::string& file_path) -> bool {
  std::ifstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }
  
  Clear();
  
  // Load parameters
  file.read(reinterpret_cast<char*>(&num_clusters_), sizeof(num_clusters_));
  file.read(reinterpret_cast<char*>(&rebuild_threshold_), sizeof(rebuild_threshold_));
  file.read(reinterpret_cast<char*>(&nprobe_), sizeof(nprobe_));
  file.read(reinterpret_cast<char*>(&vectors_since_last_rebuild_), sizeof(vectors_since_last_rebuild_));
  
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
  
  // Load centroids
  size_t centroid_count;
  file.read(reinterpret_cast<char*>(&centroid_count), sizeof(centroid_count));
  
  centroids_.resize(centroid_count);
  for (size_t i = 0; i < centroid_count; i++) {
    size_t dim;
    file.read(reinterpret_cast<char*>(&dim), sizeof(dim));
    
    centroids_[i].resize(dim);
    file.read(reinterpret_cast<char*>(centroids_[i].data()), static_cast<std::streamsize>(dim * sizeof(float)));
  }
  
  // Load inverted lists
  size_t list_count;
  file.read(reinterpret_cast<char*>(&list_count), sizeof(list_count));
  
  for (size_t i = 0; i < list_count; i++) {
    int cluster_id;
    file.read(reinterpret_cast<char*>(&cluster_id), sizeof(cluster_id));
    
    size_t id_count;
    file.read(reinterpret_cast<char*>(&id_count), sizeof(id_count));
    
    std::vector<uint64_t> vector_ids(id_count);
    file.read(reinterpret_cast<char*>(vector_ids.data()), static_cast<std::streamsize>(id_count * sizeof(uint64_t)));
    
    inverted_lists_[cluster_id] = std::move(vector_ids);
  }
  
  // Rebuild vector_to_cluster_ mapping
  for (const auto& [cluster_id, vector_ids] : inverted_lists_) {
    for (uint64_t vector_id : vector_ids) {
      vector_to_cluster_[vector_id] = cluster_id;
    }
  }
  
  return file.good();
}

auto IVF::Size() const -> size_t {
  return vectors_.size();
}

void IVF::Clear() {
  centroids_.clear();
  inverted_lists_.clear();
  vectors_.clear();
  vector_to_cluster_.clear();
  vectors_since_last_rebuild_ = 0;
}

auto IVF::GetType() const -> IndexType {
  return IndexType::kIvf;
}

// Private helper methods
auto IVF::l2_distance(const std::vector<float>& a, const std::vector<float>& b) const -> float {
  float dist = 0.0F;
  for (size_t i = 0; i < a.size(); i++) {
    float diff = a[i] - b[i];
    dist += diff * diff;
  }
  return std::sqrt(dist);
}

auto IVF::assign_to_cluster(const std::vector<float>& vector) const -> int {
  if (centroids_.empty()) {
    return -1;
  }
  
  int best_cluster = 0;
  float min_distance = std::numeric_limits<float>::max();
  
  for (size_t i = 0; i < centroids_.size(); i++) {
    float distance = l2_distance(vector, centroids_[i]);
    if (distance < min_distance) {
      min_distance = distance;
      best_cluster = static_cast<int>(i);
    }
  }
  
  return best_cluster;
}

void IVF::rebuild_clusters() {
  if (vectors_.empty()) {
    return;
  }
  
  // Clear existing clusters
  centroids_.clear();
  inverted_lists_.clear();
  vector_to_cluster_.clear();
  
  kmeans_clustering();
  
  // Reassign all vectors to clusters
  for (const auto& [id, vector] : vectors_) {
    int cluster_id = assign_to_cluster(vector);
    if (cluster_id >= 0) {
      inverted_lists_[cluster_id].push_back(id);
      vector_to_cluster_[id] = cluster_id;
    }
  }
}

void IVF::kmeans_clustering() {
  int dataset_size = static_cast<int>(vectors_.size());
  int actual_clusters = std::min(num_clusters_, dataset_size);
  
  // Initialize centroids with random vectors
  centroids_.clear();
  centroids_.resize(static_cast<size_t>(actual_clusters));
  
  std::vector<uint64_t> vector_ids;
  vector_ids.reserve(vectors_.size());
  for (const auto& [id, vector] : vectors_) {
    vector_ids.push_back(id);
  }
  
  std::random_device rd;
  std::mt19937 gen(rd());
  std::shuffle(vector_ids.begin(), vector_ids.end(), gen);
  
  // Initialize centroids with first k vectors
  for (int i = 0; i < actual_clusters; i++) {
    centroids_[static_cast<size_t>(i)] = vectors_.at(vector_ids[static_cast<size_t>(i)]);
  }
  
  // K-means iterations
  const int max_iterations = 20;
  bool changed = true;
  int iteration = 0;
  
  std::vector<int> assignments(static_cast<size_t>(dataset_size), -1);
  
  while (changed && iteration < max_iterations) {
    changed = false;
    
    // Assign each vector to nearest centroid
    size_t idx = 0;
    for (const auto& [id, vector] : vectors_) {
      int best_cluster = assign_to_cluster(vector);
      if (assignments[idx] != best_cluster) {
        assignments[idx] = best_cluster;
        changed = true;
      }
      idx++;
    }
    
    // Update centroids
    std::vector<std::vector<float>> new_centroids(static_cast<size_t>(actual_clusters));
    std::vector<int> cluster_counts(static_cast<size_t>(actual_clusters), 0);
    
    // Initialize centroids to zero
    for (int i = 0; i < actual_clusters; i++) {
      if (!centroids_.empty()) {
        new_centroids[static_cast<size_t>(i)].resize(centroids_[0].size(), 0.0F);
      }
    }
    
    // Sum vectors in each cluster
    idx = 0;
    for (const auto& [id, vector] : vectors_) {
      int cluster_id = assignments[idx];
      if (cluster_id >= 0 && cluster_id < actual_clusters) {
        for (size_t j = 0; j < vector.size(); j++) {
          new_centroids[static_cast<size_t>(cluster_id)][j] += vector[j];
        }
        cluster_counts[static_cast<size_t>(cluster_id)]++;
      }
      idx++;
    }
    
    // Average to get new centroids
    for (int i = 0; i < actual_clusters; i++) {
      if (cluster_counts[static_cast<size_t>(i)] > 0) {
        for (size_t j = 0; j < new_centroids[static_cast<size_t>(i)].size(); j++) {
          new_centroids[static_cast<size_t>(i)][j] /= static_cast<float>(cluster_counts[static_cast<size_t>(i)]);
        }
        centroids_[static_cast<size_t>(i)] = new_centroids[static_cast<size_t>(i)];
      }
    }
    
    iteration++;
  }
}

auto IVF::search_clusters(const std::vector<float>& query_vector, int nprobe) const -> std::vector<int> {
  if (centroids_.empty()) {
    return {};
  }
  
  // Calculate distances to all centroids
  std::vector<std::pair<float, int>> centroid_distances;
  for (size_t i = 0; i < centroids_.size(); i++) {
    float dist = l2_distance(query_vector, centroids_[i]);
    centroid_distances.emplace_back(dist, static_cast<int>(i));
  }
  
  // Sort by distance
  std::sort(centroid_distances.begin(), centroid_distances.end());
  
  // Return top nprobe clusters
  std::vector<int> result;
  int actual_nprobe = std::min(nprobe, static_cast<int>(centroid_distances.size()));
  result.reserve(static_cast<size_t>(actual_nprobe));
  for (int i = 0; i < actual_nprobe; i++) {
    result.push_back(centroid_distances[static_cast<size_t>(i)].second);
  }
  
  return result;
}

}  // namespace sage_flow
