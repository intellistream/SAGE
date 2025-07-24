#include "index/knn_operator.h"

#include "index/index.h"
#include <sstream>

namespace sage_flow {

auto KnnOperator::Process(std::shared_ptr<Index> index) -> bool {
  if (!index) {
    return false;
  }
  
  if (query_vector_.empty()) {
    return false;
  }
  
  results_ = index->Search(query_vector_, k_);
  return true;
}

auto KnnOperator::GetOperatorType() const -> std::string {
  return "KnnOperator";
}

auto KnnOperator::Configure(const std::string& config) -> bool {
  return ParseConfig(config);
}

void KnnOperator::SetQueryVector(const std::vector<float>& query_vector) {
  query_vector_ = query_vector;
}

void KnnOperator::SetK(size_t k) {
  k_ = k;
}

auto KnnOperator::GetResults() const -> const std::vector<SearchResult>& {
  return results_;
}

void KnnOperator::ClearResults() {
  results_.clear();
}

auto KnnOperator::ParseConfig(const std::string& config) -> bool {
  // Simple parsing for key=value pairs separated by semicolons
  std::istringstream iss(config);
  std::string pair;
  
  while (std::getline(iss, pair, ';')) {
    auto eq_pos = pair.find('=');
    if (eq_pos == std::string::npos) {
      continue;
    }
    
    std::string key = pair.substr(0, eq_pos);
    std::string value = pair.substr(eq_pos + 1);
    
    // Trim whitespace
    key.erase(0, key.find_first_not_of(" \t"));
    key.erase(key.find_last_not_of(" \t") + 1);
    value.erase(0, value.find_first_not_of(" \t"));
    value.erase(value.find_last_not_of(" \t") + 1);
    
    if (key == "k") {
      try {
        k_ = std::stoull(value);
      } catch (const std::exception&) {
        return false;
      }
    }
    // Add more configuration parameters as needed
  }
  
  return true;
}

}  // namespace sage_flow
