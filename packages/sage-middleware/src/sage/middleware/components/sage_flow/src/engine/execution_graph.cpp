#include "../../include/engine/execution_graph.hpp"

#include "../../include/operator/base_operator.hpp"

namespace sage_flow {

// Constructor and destructor are defined in header file

// Graph construction
auto ExecutionGraph::addOperator(std::shared_ptr<BaseOperator> op)
    -> OperatorId {
  if (!op) return static_cast<OperatorId>(-1);

  auto id = next_operator_id_++;
  operators_[id] = std::move(op);
  return id;
}

auto ExecutionGraph::connectOperators(OperatorId source,
                                      OperatorId target) -> void {
  if (operators_.find(source) == operators_.end() ||
      operators_.find(target) == operators_.end()) {
    return;
  }

  adjacency_list_[source].push_back(target);
  reverse_adjacency_list_[target].push_back(source);
}

auto ExecutionGraph::removeOperator(OperatorId id) -> void {
  if (operators_.find(id) == operators_.end()) {
    return;
  }

  // Remove from adjacency lists
  adjacency_list_.erase(id);
  reverse_adjacency_list_.erase(id);

  // Remove references to this operator
  for (auto& pair : adjacency_list_) {
    auto& successors = pair.second;
    // Manual removal without std::remove
    for (auto it = successors.begin(); it != successors.end();) {
      if (*it == id) {
        it = successors.erase(it);
      } else {
        ++it;
      }
    }
  }

  for (auto& pair : reverse_adjacency_list_) {
    auto& predecessors = pair.second;
    // Manual removal without std::remove
    for (auto it = predecessors.begin(); it != predecessors.end();) {
      if (*it == id) {
        it = predecessors.erase(it);
      } else {
        ++it;
      }
    }
  }

  // Remove the operator itself
  operators_.erase(id);
}

// Graph traversal
auto ExecutionGraph::getTopologicalOrder() const -> std::vector<OperatorId> {
  std::vector<OperatorId> result;
  std::unordered_map<OperatorId, bool> visited;
  std::unordered_map<OperatorId, bool> rec_stack;

  for (const auto& pair : operators_) {
    visited[pair.first] = false;
    rec_stack[pair.first] = false;
  }

  for (const auto& pair : operators_) {
    if (!visited[pair.first]) {
      topologicalSortUtil(pair.first, visited, rec_stack, result);
    }
  }

  // Reverse the result to get source-to-sink order for stream processing
  std::reverse(result.begin(), result.end());
  return result;
}

auto ExecutionGraph::getSourceOperators() const -> std::vector<OperatorId> {
  std::vector<OperatorId> sources;
  for (const auto& pair : operators_) {
    if (reverse_adjacency_list_.find(pair.first) ==
            reverse_adjacency_list_.end() ||
        reverse_adjacency_list_.at(pair.first).empty()) {
      sources.push_back(pair.first);
    }
  }
  return sources;
}

auto ExecutionGraph::getSinkOperators() const -> std::vector<OperatorId> {
  std::vector<OperatorId> sinks;
  for (const auto& pair : operators_) {
    if (adjacency_list_.find(pair.first) == adjacency_list_.end() ||
        adjacency_list_.at(pair.first).empty()) {
      sinks.push_back(pair.first);
    }
  }
  return sinks;
}

// Operator access
auto ExecutionGraph::getOperator(OperatorId id)
    -> std::shared_ptr<BaseOperator> {
  auto it = operators_.find(id);
  return (it != operators_.end()) ? it->second : nullptr;
}

auto ExecutionGraph::getOperators() const
    -> const std::unordered_map<OperatorId, std::shared_ptr<BaseOperator>>& {
  return operators_;
}

auto ExecutionGraph::getSuccessors(OperatorId id) const
    -> std::vector<OperatorId> {
  auto it = adjacency_list_.find(id);
  return (it != adjacency_list_.end()) ? it->second : std::vector<OperatorId>{};
}

auto ExecutionGraph::getPredecessors(OperatorId id) const
    -> std::vector<OperatorId> {
  auto it = reverse_adjacency_list_.find(id);
  return (it != reverse_adjacency_list_.end()) ? it->second
                                               : std::vector<OperatorId>{};
}

// Graph properties
auto ExecutionGraph::size() const -> size_t { return operators_.size(); }

auto ExecutionGraph::empty() const -> bool { return operators_.empty(); }

auto ExecutionGraph::isValid() const -> bool {
  // Check for cycles
  if (detectCycles()) {
    return false;
  }

  // Check for disconnected components (simplified check)
  if (operators_.size() > 1) {
    auto sources = getSourceOperators();
    if (sources.empty()) {
      return false;  // No source operators
    }
  }

  return true;
}

auto ExecutionGraph::validate() const -> bool { return isValid(); }

auto ExecutionGraph::getOperatorCount() const -> size_t { return size(); }

auto ExecutionGraph::isRunning() const -> bool {
  // Simplified - in practice, this would check operator states
  return false;
}

// Execution preparation
auto ExecutionGraph::initialize() -> void {
  // Initialize all operators
  for (auto& pair : operators_) {
    if (pair.second) {
      // Initialize operator - simplified
    }
  }
}

auto ExecutionGraph::finalize() -> void {
  // Finalize the graph - simplified
}

auto ExecutionGraph::reset() -> void {
  // Reset all operators and connections - simplified
}

// Private methods
auto ExecutionGraph::detectCycles() const -> bool {
  std::unordered_map<OperatorId, bool> visited;
  std::unordered_map<OperatorId, bool> rec_stack;

  for (const auto& pair : operators_) {
    visited[pair.first] = false;
    rec_stack[pair.first] = false;
  }

  std::vector<OperatorId> dummy_topo_order;
  for (const auto& pair : operators_) {
    if (!visited[pair.first] &&
        topologicalSortUtil(pair.first, visited, rec_stack, dummy_topo_order)) {
      return true;  // Cycle detected
    }
  }

  return false;
}

auto ExecutionGraph::topologicalSortUtil(
    OperatorId id, std::unordered_map<OperatorId, bool>& visited,
    std::unordered_map<OperatorId, bool>& rec_stack,
    std::vector<OperatorId>& topo_order) const -> bool {
  visited[id] = true;
  rec_stack[id] = true;

  auto it = adjacency_list_.find(id);
  if (it != adjacency_list_.end()) {
    for (auto successor : it->second) {
      if (!visited[successor]) {
        if (topologicalSortUtil(successor, visited, rec_stack, topo_order)) {
          return true;  // Cycle detected
        }
      } else if (rec_stack[successor]) {
        return true;  // Cycle detected
      }
    }
  }

  rec_stack[id] = false;
  topo_order.push_back(id);
  return false;
}

}  // namespace sage_flow
