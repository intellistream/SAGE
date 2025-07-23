#include "index/itopk_operator.h"

#include "index/index.h"
#include <algorithm>
#include <sstream>

namespace sage_flow {

auto TopKOperator::Process(std::shared_ptr<Index> index) -> bool {
  if (!index) {
    return false;
  }
  
  if (query_vector_.empty()) {
    return false;
  }
  
  auto raw_results = index->Search(query_vector_, k_);
  results_ = FilterBySimilarity(raw_results);
  
  return true;
}

auto TopKOperator::GetOperatorType() const -> std::string {
  return "TopKOperator";
}

auto TopKOperator::Configure(const std::string& config) -> bool {
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
    } else if (key == "threshold") {
      try {
        similarity_threshold_ = std::stof(value);
      } catch (const std::exception&) {
        return false;
      }
    }
  }
  
  return true;
}

void TopKOperator::SetTopK(size_t k) {
  k_ = k;
}

auto TopKOperator::GetTopK() const -> size_t {
  return k_;
}

void TopKOperator::SetQuery(const std::vector<float>& query_vector) {
  query_vector_ = query_vector;
}

auto TopKOperator::GetTopKResults() const -> std::vector<SearchResult> {
  return results_;
}

void TopKOperator::SetSimilarityThreshold(float threshold) {
  similarity_threshold_ = threshold;
}

auto TopKOperator::GetSimilarityThreshold() const -> float {
  return similarity_threshold_;
}

auto TopKOperator::FilterBySimilarity(const std::vector<SearchResult>& results) const 
    -> std::vector<SearchResult> {
  std::vector<SearchResult> filtered_results;
  
  std::copy_if(results.begin(), results.end(), 
               std::back_inserter(filtered_results),
               [this](const SearchResult& result) {
                 return result.similarity_score_ >= similarity_threshold_;
               });
  
  return filtered_results;
}

}  // namespace sage_flow
