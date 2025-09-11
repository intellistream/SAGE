#pragma once

#include <memory>
#include <unordered_map>
#include <vector>

#include "engine/execution_graph.hpp"
#include "operator/base_operator.hpp"
#include "data_stream/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

class StreamEngine {
public:
  StreamEngine();
  virtual ~StreamEngine() = default;
  
  void start();
  void stop();
  void run();
  
  void processGraph(ExecutionGraph& graph);
  
private:
  bool engine_running_ = false;
  std::shared_ptr<ExecutionGraph> graph_;
  std::unordered_map<ExecutionGraph::OperatorId, std::vector<std::shared_ptr<MultiModalMessage>>> intermediate_results_;

  std::shared_ptr<MultiModalMessage> getInputForOperator(ExecutionGraph::OperatorId op_id);
};

}  // namespace sage_flow
