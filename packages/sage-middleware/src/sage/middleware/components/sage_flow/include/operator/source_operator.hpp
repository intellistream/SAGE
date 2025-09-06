#pragma once

#include <memory>
#include <string>

#include "base_operator.hpp"

namespace sage_flow {

#include "message/multimodal_message.hpp"

using ResponseType = Response<MultiModalMessage>;

/**
 * @brief Source operator for data ingestion
 *
 * Generates data from various sources (files, streams, etc.) and emits
 * MultiModalMessage objects into the processing pipeline.
 */
class SourceOperator : public BaseOperator<MultiModalMessage, MultiModalMessage> {
public:
  explicit SourceOperator(std::string name);

  // Prevent copying
  SourceOperator(const SourceOperator&) = delete;
  auto operator=(const SourceOperator&) -> SourceOperator& = delete;

  // Allow moving
  SourceOperator(SourceOperator&&) = default;
  auto operator=(SourceOperator&&) -> SourceOperator& = default;

  auto process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<ResponseType> override;

  // Source-specific interface
  virtual auto hasNext() -> bool = 0;
  virtual auto next() -> std::unique_ptr<MultiModalMessage> = 0;
  virtual auto reset() -> void = 0;

protected:
  auto runSource() -> void;
};

}  // namespace sage_flow
