#include "operator/topk_operator.h"

#include "operator/response.h"
#include <algorithm>
#include <utility>

namespace sage_flow {

TopKOperator::TopKOperator(std::string name, size_t k)
    : Operator(OperatorType::kTopK, std::move(name)), k_(k) {
  top_k_elements_.reserve(k_);
}

auto TopKOperator::process(Response& input_record, int slot) -> bool {
  (void)slot; // Suppress unused parameter warning
  
  if (!input_record.hasMessage()) {
    return false;
  }
  
  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }
  
  incrementProcessedCount();
  insertElement(std::move(input_message));
  
  return true;
}

auto TopKOperator::setK(size_t k) -> void {
  k_ = k;
  top_k_elements_.reserve(k_);
  maintainTopK();
}

auto TopKOperator::getK() const -> size_t {
  return k_;
}

auto TopKOperator::getTopK() const -> std::vector<std::unique_ptr<MultiModalMessage>> {
  // Create copies of the top-k elements
  std::vector<std::unique_ptr<MultiModalMessage>> result;
  result.reserve(top_k_elements_.size());
  
  // Note: This would require a deep copy mechanism for MultiModalMessage
  // For now, we return an empty vector as a placeholder
  return result;
}

auto TopKOperator::insertElement(std::unique_ptr<MultiModalMessage> message) -> void {
  if (!message) {
    return;
  }
  
  float score = getScore(*message);
  
  if (top_k_elements_.size() < k_) {
    // Still have space, just insert
    top_k_elements_.push_back(std::move(message));
  } else {
    // Find the element with minimum score
    auto min_it = std::min_element(top_k_elements_.begin(), top_k_elements_.end(),
                                  [this](const std::unique_ptr<MultiModalMessage>& a,
                                         const std::unique_ptr<MultiModalMessage>& b) {
                                    return getScore(*a) < getScore(*b);
                                  });
    
    if (min_it != top_k_elements_.end() && getScore(**min_it) < score) {
      // Replace the minimum element
      *min_it = std::move(message);
    }
  }
  
  maintainTopK();
}

auto TopKOperator::maintainTopK() -> void {
  if (top_k_elements_.size() > k_) {
    // Sort and keep only top k
    std::partial_sort(top_k_elements_.begin(), 
                     top_k_elements_.begin() + static_cast<std::ptrdiff_t>(k_),
                     top_k_elements_.end(),
                     [this](const std::unique_ptr<MultiModalMessage>& a,
                            const std::unique_ptr<MultiModalMessage>& b) {
                       return getScore(*a) > getScore(*b);
                     });
    
    top_k_elements_.resize(k_);
  }
}

}  // namespace sage_flow
