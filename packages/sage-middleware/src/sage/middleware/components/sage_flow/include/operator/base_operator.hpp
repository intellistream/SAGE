#pragma once

#include <cstdint>
#include <functional>
#include <string>

#include "operator_types.hpp"

namespace sage_flow {

class Response;

/**
 * @brief Base class for all SAGE flow operators
 *
 * This class provides the fundamental interface for all data processing
 * operators in the SAGE flow framework. It follows Google C++ Style Guide
 * conventions and ensures compatibility with the sage_core operator system.
 */
class BaseOperator {
public:
  virtual ~BaseOperator() = default;

  explicit BaseOperator(OperatorType type);
  explicit BaseOperator(OperatorType type, std::string name);

  // Prevent copying
  BaseOperator(const BaseOperator&) = delete;
  auto operator=(const BaseOperator&) -> BaseOperator& = delete;

  // Allow moving
  BaseOperator(BaseOperator&&) = default;
  auto operator=(BaseOperator&&) -> BaseOperator& = default;

  // Emit callback type
  using EmitCallback = std::function<void(int, Response&)>;

  // Core operator interface
  virtual auto open() -> void;
  virtual auto close() -> void;
  virtual auto process(Response& input_record, int slot) -> bool = 0;
  virtual auto emit(int output_id, Response& output_record) const -> void;

  // Emit callback management
  auto setEmitCallback(EmitCallback callback) -> void;
  auto getEmitCallback() const -> const EmitCallback&;

  // Accessors
  auto getType() const -> OperatorType;
  auto getName() const -> const std::string&;
  auto setName(std::string name) -> void;

  // Performance monitoring
  auto getProcessedCount() const -> uint64_t;
  auto getOutputCount() const -> uint64_t;
  auto resetCounters() -> void;

protected:
  // Protected members for derived classes
  OperatorType type_;
  std::string name_;
  uint64_t processed_count_ = 0;
  uint64_t output_count_ = 0;
  EmitCallback emit_callback_;

  // Utility methods for derived classes
  auto incrementProcessedCount() -> void;
  auto incrementOutputCount() -> void;
};

}  // namespace sage_flow
