#include "operator/source_operator.hpp"
#include "operator/topk_operator.hpp"

#include <algorithm>
#include <utility>

#include "operator/response.hpp"

namespace sage_flow {

TopKOperator::TopKOperator(std::string name, size_t k)
    : BaseOperator(OperatorType::kTopK, std::move(name)), k_(k) {
  top_k_elements_.reserve(k_);
}

auto TopKOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<ResponseType> {
  for (const auto& message : input) {
    if (message) {
      incrementProcessedCount();
      insertElement(message);
    }
  }
  return std::nullopt;  // TopK doesn't produce output in this implementation
}

auto TopKOperator::setK(size_t k) -> void {
  k_ = k;
  top_k_elements_.reserve(k_);
  maintainTopK();
}

auto TopKOperator::getK() const -> size_t { return k_; }

auto TopKOperator::getTopK() const
    -> std::vector<std::shared_ptr<MultiModalMessage>> {
  return top_k_elements_;
}

auto TopKOperator::insertElement(std::shared_ptr<MultiModalMessage> message)
    -> void {
  if (!message) {
    return;
  }

  float score = getScore(*message);

  if (top_k_elements_.size() < k_) {
    // Still have space, just insert
    top_k_elements_.push_back(message);
  } else {
    // Find the element with minimum score
    auto min_it =
        std::min_element(top_k_elements_.begin(), top_k_elements_.end(),
                         [this](const std::shared_ptr<MultiModalMessage>& a,
                                const std::shared_ptr<MultiModalMessage>& b) {
                           return getScore(*a) < getScore(*b);
                         });

    if (min_it != top_k_elements_.end() && getScore(**min_it) < score) {
      // Replace the minimum element
      *min_it = message;
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
                      [this](const std::shared_ptr<MultiModalMessage>& a,
                             const std::shared_ptr<MultiModalMessage>& b) {
                        return getScore(*a) > getScore(*b);
                      });

    top_k_elements_.resize(k_);
  }
}

}  // namespace sage_flow
