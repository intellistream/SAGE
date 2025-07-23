#include "index/brute_force_index.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <numeric>
#include <vector>

namespace sage_flow {

auto BruteForceIndex::Initialize(const IndexConfig& config) -> bool {
  config_ = config;
  vectors_.clear();
  return true;
}

auto BruteForceIndex::AddVector(uint64_t id, const std::vector<float>& vector) -> bool {
  if (vector.size() != config_.dimension_) {
    return false;
  }
  
  if (vectors_.size() >= config_.max_elements_) {
    return false;
  }
  
  vectors_[id] = vector;
  return true;
}

auto BruteForceIndex::Search(const std::vector<float>& query_vector, size_t k) const 
    -> std::vector<SearchResult> {
  if (query_vector.size() != config_.dimension_) {
    return {};
  }
  
  std::vector<SearchResult> results;
  results.reserve(vectors_.size());
  
  for (const auto& [id, vector] : vectors_) {
    float distance = 0.0F;
    float similarity = 0.0F;
    
    if (config_.distance_metric_ == "euclidean") {
      distance = CalculateEuclideanDistance(query_vector, vector);
      similarity = 1.0F / (1.0F + distance);
    } else if (config_.distance_metric_ == "dot") {
      // Dot product similarity
      similarity = std::inner_product(query_vector.begin(), query_vector.end(), 
                                    vector.begin(), 0.0F);
      distance = -similarity;  // Higher dot product = lower distance
    } else {
      // Default to cosine (covers both "cosine" and unknown metrics)
      similarity = CalculateCosineSimilarity(query_vector, vector);
      distance = 1.0F - similarity;
    }
    
    results.emplace_back(id, distance, similarity);
  }
  
  // Sort by distance (ascending) and take top k
  std::partial_sort(results.begin(), 
                   results.begin() + static_cast<std::ptrdiff_t>(std::min(k, results.size())),
                   results.end(),
                   [](const SearchResult& a, const SearchResult& b) {
                     return a.distance_ < b.distance_;
                   });
  
  if (results.size() > k) {
    results.resize(k);
  }
  
  return results;
}

auto BruteForceIndex::Build() -> bool {
  // No-op for brute force index
  return true;
}

auto BruteForceIndex::SaveIndex(const std::string& file_path) const -> bool {
  std::ofstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }
  
  // Save configuration
  file.write(reinterpret_cast<const char*>(&config_.type_), sizeof(config_.type_));
  file.write(reinterpret_cast<const char*>(&config_.dimension_), sizeof(config_.dimension_));
  file.write(reinterpret_cast<const char*>(&config_.max_elements_), sizeof(config_.max_elements_));
  
  // Save distance metric
  size_t metric_size = config_.distance_metric_.size();
  file.write(reinterpret_cast<const char*>(&metric_size), sizeof(metric_size));
  file.write(config_.distance_metric_.data(), static_cast<std::streamsize>(metric_size));
  
  // Save vectors
  size_t num_vectors = vectors_.size();
  file.write(reinterpret_cast<const char*>(&num_vectors), sizeof(num_vectors));
  
  for (const auto& [id, vector] : vectors_) {
    file.write(reinterpret_cast<const char*>(&id), sizeof(id));
    file.write(reinterpret_cast<const char*>(vector.data()), 
               static_cast<std::streamsize>(vector.size() * sizeof(float)));
  }
  
  return file.good();
}

auto BruteForceIndex::LoadIndex(const std::string& file_path) -> bool {
  std::ifstream file(file_path, std::ios::binary);
  if (!file.is_open()) {
    return false;
  }
  
  // Load configuration
  file.read(reinterpret_cast<char*>(&config_.type_), sizeof(config_.type_));
  file.read(reinterpret_cast<char*>(&config_.dimension_), sizeof(config_.dimension_));
  file.read(reinterpret_cast<char*>(&config_.max_elements_), sizeof(config_.max_elements_));
  
  // Load distance metric
  size_t metric_size = 0;
  file.read(reinterpret_cast<char*>(&metric_size), sizeof(metric_size));
  config_.distance_metric_.resize(metric_size);
  file.read(config_.distance_metric_.data(), static_cast<std::streamsize>(metric_size));
  
  // Load vectors
  size_t num_vectors = 0;
  file.read(reinterpret_cast<char*>(&num_vectors), sizeof(num_vectors));
  
  vectors_.clear();
  vectors_.reserve(num_vectors);
  
  for (size_t i = 0; i < num_vectors; ++i) {
    uint64_t id = 0;
    file.read(reinterpret_cast<char*>(&id), sizeof(id));
    
    std::vector<float> vector(config_.dimension_);
    file.read(reinterpret_cast<char*>(vector.data()), 
              static_cast<std::streamsize>(vector.size() * sizeof(float)));
    
    vectors_[id] = std::move(vector);
  }
  
  return file.good();
}

auto BruteForceIndex::Size() const -> size_t {
  return vectors_.size();
}

void BruteForceIndex::Clear() {
  vectors_.clear();
}

auto BruteForceIndex::GetType() const -> IndexType {
  return IndexType::kBruteForce;
}

auto BruteForceIndex::CalculateCosineSimilarity(const std::vector<float>& vec1, 
                                              const std::vector<float>& vec2) const -> float {
  if (vec1.size() != vec2.size()) {
    return 0.0F;
  }
  
  float dot_product = std::inner_product(vec1.begin(), vec1.end(), vec2.begin(), 0.0F);
  
  float norm1 = std::sqrt(std::inner_product(vec1.begin(), vec1.end(), vec1.begin(), 0.0F));
  float norm2 = std::sqrt(std::inner_product(vec2.begin(), vec2.end(), vec2.begin(), 0.0F));
  
  if (norm1 == 0.0F || norm2 == 0.0F) {
    return 0.0F;
  }
  
  return dot_product / (norm1 * norm2);
}

auto BruteForceIndex::CalculateEuclideanDistance(const std::vector<float>& vec1, 
                                               const std::vector<float>& vec2) const -> float {
  if (vec1.size() != vec2.size()) {
    return std::numeric_limits<float>::max();
  }
  
  float distance = 0.0F;
  for (size_t i = 0; i < vec1.size(); ++i) {
    float diff = vec1[i] - vec2[i];
    distance += diff * diff;
  }
  
  return std::sqrt(distance);
}

}  // namespace sage_flow
