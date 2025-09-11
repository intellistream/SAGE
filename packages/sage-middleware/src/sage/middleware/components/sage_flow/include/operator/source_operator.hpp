#pragma once

#include <memory>
#include <string>

#include "base_operator.hpp"

namespace sage_flow {



/**
 * @brief Source operator for data ingestion
 *
 * Generates data from various sources (files, streams, etc.) and emits
 * MultiModalMessage objects into the processing pipeline.
 */
template <typename InputType >
class SourceOperator : public BaseOperator<InputType, InputType> {
public:
  explicit SourceOperator(std::string name);

  // Prevent copying
  SourceOperator(const SourceOperator&) = delete;
  auto operator=(const SourceOperator&) -> SourceOperator& = delete;

  // Allow moving
  SourceOperator(SourceOperator&&) = default;
  auto operator=(SourceOperator&&) -> SourceOperator& = default;

  auto process(const std::vector<std::shared_ptr<InputType>>& input) -> std::optional<Response<InputType>> override;

  // Source-specific interface
  virtual auto hasNext() -> bool = 0;
  virtual auto next() -> std::unique_ptr<InputType> = 0;
  virtual auto reset() -> void = 0;

protected:
  auto runSource() -> void;
};

}  // namespace sage_flow
