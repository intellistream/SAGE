#pragma once

#include <memory>
#include <queue>
#include <unordered_map>
#include <vector>
#include "message/multimodal_message.hpp"
#include "operator/base_operator.hpp"

namespace sage_flow {

/**
 * @brief Execution graph for stream processing operators
 *
 * Manages the topology and execution order of operators in a stream
 * processing pipeline.
 */
class ExecutionGraph {
public:
  using OperatorId = size_t;

  ExecutionGraph() = default;
  ~ExecutionGraph() = default;

  // Prevent copying
  ExecutionGraph(const ExecutionGraph&) = delete;
  auto operator=(const ExecutionGraph&) -> ExecutionGraph& = delete;

  // Allow moving
  ExecutionGraph(ExecutionGraph&&) = default;
  auto operator=(ExecutionGraph&&) -> ExecutionGraph& = default;

  // Graph construction
  auto addOperator(std::shared_ptr<BaseOperator<MultiModalMessage, MultiModalMessage>> op) -> OperatorId;
  auto connectOperators(OperatorId source, OperatorId target) -> void;
  auto removeOperator(OperatorId id) -> void;

  // Graph traversal
  auto getTopologicalOrder() const -> std::vector<OperatorId>;
  auto getSourceOperators() const -> std::vector<OperatorId>;
  auto getSinkOperators() const -> std::vector<OperatorId>;

  // Operator access
  auto getOperator(OperatorId id) -> std::shared_ptr<BaseOperator<MultiModalMessage, MultiModalMessage>>;
  auto getOperators() const
      -> const std::unordered_map<OperatorId, std::shared_ptr<BaseOperator<MultiModalMessage, MultiModalMessage>>>&;
  auto getSuccessors(OperatorId id) const -> std::vector<OperatorId>;
  auto getPredecessors(OperatorId id) const -> std::vector<OperatorId>;

  // Graph properties
  auto size() const -> size_t;
  auto empty() const -> bool;
  auto isValid() const -> bool;   // Check for cycles, disconnected components
  auto validate() const -> bool;  // Alias for isValid
  auto getOperatorCount() const -> size_t;  // Alias for size
  auto isRunning() const -> bool;

  // Execution preparation
  auto initialize() -> void;
  auto finalize() -> void;
  auto reset() -> void;

private:
  std::unordered_map<OperatorId, std::shared_ptr<BaseOperator<MultiModalMessage, MultiModalMessage>>> operators_;
  std::unordered_map<OperatorId, std::vector<OperatorId>> adjacency_list_;
  std::unordered_map<OperatorId, std::vector<OperatorId>>
      reverse_adjacency_list_;
  OperatorId next_operator_id_ = 0;

  // Internal methods
  auto detectCycles() const -> bool;
  auto topologicalSortUtil(OperatorId id,
                           std::unordered_map<OperatorId, bool>& visited,
                           std::unordered_map<OperatorId, bool>& rec_stack,
                           std::vector<OperatorId>& topo_order) const -> bool;
};

}  // namespace sage_flow
