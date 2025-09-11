#pragma once

#include <queue>
#include <vector>
#include <functional>

#include "base_operator.hpp"
#include "data_stream/response.hpp"

namespace sage_flow {

template <typename T>
class TopKOperator : public BaseOperator<T, T> {
public:
  using CompareFunc = std::function<bool(const T&, const T&)>;
  
  TopKOperator(std::string name, size_t k, CompareFunc compare_func);
  TopKOperator(std::string name, size_t k, CompareFunc compare_func, std::string description);
  
  // Prevent copying
  TopKOperator(const TopKOperator&) = delete;
  auto operator=(const TopKOperator&) -> TopKOperator& = delete;
  
  // Allow moving
  TopKOperator(TopKOperator&&) = default;
  auto operator=(TopKOperator&&) -> TopKOperator& = default;
  
  auto process(const std::vector<std::unique_ptr<T>>& input) -> std::optional<Response<T>> override;
  
  auto getK() const -> size_t;
  auto getCompareFunc() const -> const CompareFunc&;
  
private:
  size_t k_;
  CompareFunc compare_func_;
  std::priority_queue<T, std::vector<T>, CompareFunc> top_k_queue_;
};

}  // namespace sage_flow