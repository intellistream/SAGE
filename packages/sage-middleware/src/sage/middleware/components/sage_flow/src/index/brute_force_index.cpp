#include "index/brute_force_index.hpp"

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

auto BruteForceIndex::add_vector(const std::vector<double>& vec) -> int {
  if (vec.size() != config_.dimension_) {
    return -1;
  }

  if (vectors_.size() >= config_.max_elements_) {
    return -1;
  }

  vectors_.push_back(vec);
  return static_cast<int>(vectors_.size() - 1);
}

auto BruteForceIndex::search_kNN(const std::vector<double>& query, size_t k) const -> std::vector<std::pair<int, double>> {
  if (query.size() != config_.dimension_) {
    return {};
  }

  std::vector<std::pair<int, double>> results;
  results.reserve(vectors_.size());

  for (int i = 0; i < static_cast<int>(vectors_.size()); ++i) {
    double distance = calculate_euclidean_distance(query, vectors_[i]);
    results.emplace_back(i, distance);
  }

  // Sort by distance ascending and take top k
  std::partial_sort(results.begin(), results.begin() + static_cast<std::ptrdiff_t>(std::min(k, results.size())), results.end(),
                    [](const std::pair<int, double>& a, const std::pair<int, double>& b) {
                      return a.second < b.second;
                    });

  if (results.size() > k) {
    results.resize(k);
  }

  return results;
}

auto BruteForceIndex::RemoveVector(uint64_t id) -> bool {
  // Placeholder, remove by id if needed
  return false;
}

auto BruteForceIndex::AddVector(uint64_t id, const std::vector<float>& vector) -> bool {
  // Convert float to double
  std::vector<double> vec_double(vector.begin(), vector.end());
  int index = add_vector(vec_double);
  // Note: id not used for indexing here, assume sequential
  return index >= 0;
}

auto BruteForceIndex::Search(const std::vector<float>& query_vector,
                             size_t k) const -> std::vector<SearchResult> {
  // Convert to double for compatibility
  std::vector<double> query(query_vector.begin(), query_vector.end());
  auto knn_results = search_kNN(query, k);
  std::vector<SearchResult> results;
  for (const auto& p : knn_results) {
    results.emplace_back(static_cast<uint64_t>(p.first), static_cast<float>(p.second), 1.0f / (1.0f + static_cast<float>(p.second)));
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
  file.write(reinterpret_cast<const char*>(&config_.type_),
             sizeof(config_.type_));
  file.write(reinterpret_cast<const char*>(&config_.dimension_),
             sizeof(config_.dimension_));
  file.write(reinterpret_cast<const char*>(&config_.max_elements_),
             sizeof(config_.max_elements_));

  // Save distance metric
  size_t metric_size = config_.distance_metric_.size();
  file.write(reinterpret_cast<const char*>(&metric_size), sizeof(metric_size));
  file.write(config_.distance_metric_.data(),
             static_cast<std::streamsize>(metric_size));

  // Save vectors
  size_t num_vectors = vectors_.size();
  file.write(reinterpret_cast<const char*>(&num_vectors), sizeof(num_vectors));

  for (const auto& vec : vectors_) {
    size_t vec_size = vec.size();
    file.write(reinterpret_cast<const char*>(&vec_size), sizeof(vec_size));
    file.write(reinterpret_cast<const char*>(vec.data()),
               static_cast<std::streamsize>(vec.size() * sizeof(double)));
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
  file.read(reinterpret_cast<char*>(&config_.dimension_),
            sizeof(config_.dimension_));
  file.read(reinterpret_cast<char*>(&config_.max_elements_),
            sizeof(config_.max_elements_));

  // Load distance metric
  size_t metric_size = 0;
  file.read(reinterpret_cast<char*>(&metric_size), sizeof(metric_size));
  config_.distance_metric_.resize(metric_size);
  file.read(config_.distance_metric_.data(),
            static_cast<std::streamsize>(metric_size));

  // Load vectors
  size_t num_vectors = 0;
  file.read(reinterpret_cast<char*>(&num_vectors), sizeof(num_vectors));

  vectors_.clear();
  vectors_.reserve(num_vectors);

  for (size_t i = 0; i < num_vectors; ++i) {
    size_t vec_size = 0;
    file.read(reinterpret_cast<char*>(&vec_size), sizeof(vec_size));
    std::vector<double> vec(vec_size);
    file.read(reinterpret_cast<char*>(vec.data()),
              static_cast<std::streamsize>(vec.size() * sizeof(double)));

    vectors_.push_back(std::move(vec));
  }

  return file.good();
}

auto BruteForceIndex::Size() const -> size_t { return vectors_.size(); }

void BruteForceIndex::Clear() { vectors_.clear(); }

auto BruteForceIndex::GetType() const -> IndexType {
  return IndexType::kBruteForce;
}

auto BruteForceIndex::execute(FunctionResponse& response) -> FunctionResponse {
  FunctionResponse new_response;
  for (auto& msg : response.getMessages()) {
    // Assume msg is MultiModalMessage*
    MultiModalMessage* input_msg = msg.get();
    std::vector<double> embeddings = input_msg->getEmbeddings();
    int index = add_vector(embeddings);
    if (index >= 0) {
      auto result_msg = std::make_unique<MultiModalMessage>(input_msg->getUid());
      result_msg->setCustomField("index_added", std::to_string(index));
      new_response.addMessage(std::move(result_msg));
    }
  }
  return new_response;
}

auto BruteForceIndex::calculate_euclidean_distance(
    const std::vector<double>& vec1,
    const std::vector<double>& vec2) const -> double {
  if (vec1.size() != vec2.size()) {
    return std::numeric_limits<double>::max();
  }

  double distance = 0.0;
  for (size_t i = 0; i < vec1.size(); ++i) {
    double diff = vec1[i] - vec2[i];
    distance += diff * diff;
  }

  return std::sqrt(distance);
}

}  // namespace sage_flow
