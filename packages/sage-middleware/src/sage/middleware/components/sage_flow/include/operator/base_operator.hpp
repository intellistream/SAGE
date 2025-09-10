#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <vector>
#include <memory>
#include <optional>

#include "operator_types.hpp"
#include "operator/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

template <typename InputType = MultiModalMessage, typename OutputType = MultiModalMessage>
class BaseOperator {
public:
  virtual ~BaseOperator() = default;

  explicit BaseOperator(OperatorType type);
  explicit BaseOperator(OperatorType type, std::string name);
  explicit BaseOperator(OperatorType type, std::string name, std::string description);

  // Prevent copying
  BaseOperator(const BaseOperator&) = delete;
  auto operator=(const BaseOperator&) -> BaseOperator& = delete;

  // Allow moving
  BaseOperator(BaseOperator&&) = default;
  auto operator=(BaseOperator&&) -> BaseOperator& = default;

  // Emit callback type
  using EmitCallback = std::function<void(int, Response<OutputType>&)>;

  // Core operator interface
  virtual auto open() -> void;
  virtual auto close() -> void;
  virtual auto process(const std::vector<std::shared_ptr<InputType>>& input) -> std::optional<Response<OutputType>> = 0;
  // For Function integration
  virtual auto process(const InputType& input, Response<OutputType>& output) -> void;
  virtual auto emit(int output_id, Response<OutputType>& output_record) const -> void;

  // Emit callback management
  auto setEmitCallback(EmitCallback callback) -> void;
  auto getEmitCallback() const -> const EmitCallback&;

  // Accessors
  auto getType() const -> OperatorType;
  auto getName() const -> const std::string&;
  auto getDescription() const -> const std::string&;
  auto setName(std::string name) -> void;
  auto setDescription(std::string description) -> void;

  // Performance monitoring
  auto getProcessedCount() const -> uint64_t;
  auto getOutputCount() const -> uint64_t;
  auto resetCounters() -> void;

  // Constants
  static constexpr size_t kDefaultBatchSize = 1000;
  static constexpr int kDefaultOutputSlot = 0;

protected:
  // Protected members for derived classes
  OperatorType type_;
  std::string name_;
  std::string description_;
  uint64_t processed_count_ = 0;
  uint64_t output_count_ = 0;
  EmitCallback emit_callback_;

  // Utility methods for derived classes
  auto incrementProcessedCount() -> void;
  auto incrementOutputCount() -> void;

  // Optional support for empty responses
  static auto createEmptyResponse() -> std::optional<Response<OutputType>>;
};

}  // namespace sage_flow
