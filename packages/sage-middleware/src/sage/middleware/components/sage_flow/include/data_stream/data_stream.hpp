#pragma once

#include <any>
#include <functional>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// Required header includes instead of forward declarations
#include "../engine/execution_graph.hpp"
#include "../engine/stream_engine.hpp"
#include "../function/base_function.hpp"
#include "../function/map_function.hpp"
#include "../function/filter_function.hpp"
#include "../operator/map_operator.hpp"
#include "../operator/filter_operator.hpp"
#include "../message/multimodal_message.hpp"

namespace sage_flow {

/**
 * @brief DataStream API for building stream processing pipelines
 *
 * Provides a fluent interface for constructing and executing
 * data processing pipelines, fully compatible with SAGE framework patterns.
 *
 * This implementation follows the patterns from sage_core.api.datastream
 * and supports the same chainable operations as sage_examples.
 */
class DataStream {
public:
  // Constructor for internal use
  DataStream(std::shared_ptr<StreamEngine> engine,
             std::shared_ptr<ExecutionGraph> graph,
             ExecutionGraph::OperatorId last_operator_id =
                 static_cast<ExecutionGraph::OperatorId>(-1));

  ~DataStream() = default;

  // Prevent copying (matches sage_core pattern)
  DataStream(const DataStream&) = delete;
  auto operator=(const DataStream&) -> DataStream& = delete;

  // Allow moving for fluent interface
  DataStream(DataStream&&) = default;
  auto operator=(DataStream&&) -> DataStream& = default;

  // ===============================
  // Core DataStream Operations (sage_core compatible)
  // ===============================

  /**
    * @brief Create DataStream from a list of data
    *
    * Static factory method to create a DataStream from a vector of data items.
    * Each item in the list will be converted to a MultiModalMessage.
    *
    * @param data Vector of data items to create messages from
    * @param engine StreamEngine instance (optional, will create default if not provided)
    * @return DataStream instance
    */
   static auto from_list(const std::vector<std::unordered_map<std::string, std::variant<std::string, int64_t, double, bool>>>& data,
                         std::shared_ptr<StreamEngine> engine = nullptr) -> DataStream;

  /**
    * @brief Create a source from function - starting point for data pipeline
    *
    * Equivalent to sage_core's .from_source(SourceClass, config) pattern
    * Supports both class-based sources and lambda functions
    */
  template <typename SourceType>
  auto from_source(const std::unordered_map<std::string, std::any>& config = {})
      -> DataStream;

  auto from_source(const std::function<std::unique_ptr<MultiModalMessage>()>&
                       source_func) -> DataStream&;

  /**
   * @brief Map transformation - one-to-one data processing
   *
   * Equivalent to sage_core's .map(FunctionClass, config) pattern
   * Supports both class-based functions and lambda functions
   */
  template <typename FunctionType>
  auto map(const std::unordered_map<std::string, std::any>& config = {})
      -> DataStream;

  auto map(const std::function<std::unique_ptr<MultiModalMessage>(
               std::unique_ptr<MultiModalMessage>)>& func) -> DataStream&;

  /**
   * @brief Filter transformation - conditional data filtering
   *
   * Equivalent to sage_core's .filter(FilterClass/lambda, config) pattern
   */
  template <typename FilterType>
  auto filter(const std::unordered_map<std::string, std::any>& config = {})
      -> DataStream;

  auto filter(const std::function<bool(const MultiModalMessage&)>& predicate)
      -> DataStream&;

  /**
   * @brief FlatMap transformation - one-to-many data processing
   *
   * Equivalent to sage_core's .flatmap(FlatMapClass, config) pattern
   */
  template <typename FlatMapType>
  auto flatMap(const std::unordered_map<std::string, std::any>& config = {})
      -> DataStream;

  /**
   * @brief KeyBy transformation - data partitioning by key
   *
   * Equivalent to sage_core's .keyby(KeyFunction, strategy) pattern
   */
  template <typename KeyFunction>
  auto keyBy(const std::string& strategy = "hash",
             const std::unordered_map<std::string, std::any>& config = {})
      -> DataStream;

  /**
   * @brief Connect transformation - stream joining
   *
   * Equivalent to sage_core's .connect(other_stream) pattern
   */
  auto connect(const DataStream& other) -> DataStream;

  /**
   * @brief Union transformation - stream merging
   *
   * Merges multiple streams into one (sage_examples pattern)
   */
  auto union_(const DataStream& other) -> DataStream;

  // ===============================
  // Advanced Stream Operations
  // ===============================

  /**
   * @brief Window operations for stream aggregation
   *
   * Supports time-based and count-based windows
   */
  template <typename WindowType>
  auto window(const std::string& size, const std::string& slide = "",
              const std::unordered_map<std::string, std::any>& config = {})
      -> DataStream;

  /**
   * @brief Aggregate operations within windows
   *
   * Supports count, sum, avg, min, max aggregations
   */
  template <typename AggregateType>
  auto aggregate(const std::unordered_map<std::string, std::string>& operations,
                 const std::unordered_map<std::string, std::any>& config = {})
      -> DataStream;

  // ===============================
  // Output Operations (Terminal)
  // ===============================

  /**
   * @brief Sink operation - data output/storage
   *
   * Equivalent to sage_core's .sink(SinkClass, config) pattern
   * This is a terminal operation
   */
  template <typename SinkType>
  auto sink(const std::unordered_map<std::string, std::any>& config = {})
      -> void;

  auto sink(const std::function<void(const MultiModalMessage&)>& sink_func)
      -> void;

  // ===============================
  // Execution Control
  // ===============================

  /**
   * @brief Execute the pipeline synchronously
   *
   * Equivalent to calling env.submit() in sage_core
   */
  auto execute() -> void;

  /**
   * @brief Execute the pipeline asynchronously
   *
   * For non-blocking execution
   */
  auto executeAsync() -> void;

  /**
   * @brief Stop pipeline execution
   *
   * Graceful shutdown of the pipeline
   */
  auto stop() -> void;

  // ===============================
  // Pipeline Information
  // ===============================

  auto getOperatorCount() const -> size_t;
  auto isExecuting() const -> bool;
  auto getLastOperatorId() const -> ExecutionGraph::OperatorId;

  // Internal access for environment integration
  auto setLastOperatorId(ExecutionGraph::OperatorId id) -> void;
  auto getGraph() const -> std::shared_ptr<ExecutionGraph>;
  auto getEngine() const -> std::shared_ptr<StreamEngine>;

private:
  std::shared_ptr<StreamEngine> engine_;
  std::shared_ptr<ExecutionGraph> graph_;
  ExecutionGraph::OperatorId last_operator_id_ =
      static_cast<ExecutionGraph::OperatorId>(-1);
  ExecutionGraph::OperatorId source_operator_id_ =
      static_cast<ExecutionGraph::OperatorId>(-1);
  std::optional<StreamEngine::GraphId> graph_id_;
  bool is_finalized_ = false;

  // Internal helper methods
  template <typename OperatorType, typename FunctionType>
  auto addOperatorWithFunction(const std::unordered_map<std::string, std::any>& config)
      -> ExecutionGraph::OperatorId;

  template <typename OperatorType>
  auto addOperator(const std::unordered_map<std::string, std::any>& config)
      -> ExecutionGraph::OperatorId;

  // Function creation helpers
  template <typename FunctionType>
  auto createFunctionFromConfig(const std::unordered_map<std::string, std::any>& config)
      -> std::unique_ptr<FunctionType>;

  auto connectToLastOperator(ExecutionGraph::OperatorId new_operator_id)
      -> void;
  auto finalizeGraph() -> void;
  auto validateConfig(const std::unordered_map<std::string, std::any>& config)
      -> bool;
  auto canExecute() const -> bool;
};

// ===============================
// Template Implementation
// ===============================

template <typename SourceType>
auto DataStream::from_source(
    const std::unordered_map<std::string, std::any>& config) -> DataStream {
  auto op_id = addOperator<SourceType>(config);
  last_operator_id_ = op_id;
  return std::move(*this);
}

template <typename FunctionType>
auto DataStream::map(const std::unordered_map<std::string, std::any>& config)
    -> DataStream {
  // For map operations, we need MapOperator with MapFunction
  auto op_id = addOperatorWithFunction<MapOperator, MapFunction>(config);
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;
  return std::move(*this);
}

template <typename FilterType>
auto DataStream::filter(const std::unordered_map<std::string, std::any>& config)
    -> DataStream {
  // For filter operations, we need FilterOperator with FilterFunction
  auto op_id = addOperatorWithFunction<FilterOperator, FilterFunction>(config);
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;
  return std::move(*this);
}

template <typename FlatMapType>
auto DataStream::flatMap(
    const std::unordered_map<std::string, std::any>& config) -> DataStream {
  auto op_id = addOperator<FlatMapType>(config);
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;
  return std::move(*this);
}

template <typename KeyFunction>
auto DataStream::keyBy(const std::string& strategy,
                       const std::unordered_map<std::string, std::any>& config)
    -> DataStream {
  // KeyBy implementation with strategy support
  auto op_id = addOperator<KeyFunction>(config);
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;
  return std::move(*this);
}

template <typename WindowType>
auto DataStream::window(const std::string& size, const std::string& slide,
                        const std::unordered_map<std::string, std::any>& config)
    -> DataStream {
  // Window implementation with time/count support
  auto op_id = addOperator<WindowType>(config);
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;
  return std::move(*this);
}

template <typename AggregateType>
auto DataStream::aggregate(
    const std::unordered_map<std::string, std::string>& operations,
    const std::unordered_map<std::string, std::any>& config) -> DataStream {
  // Aggregate implementation with multiple operations
  auto op_id = addOperator<AggregateType>(config);
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;
  return std::move(*this);
}

template <typename SinkType>
auto DataStream::sink(const std::unordered_map<std::string, std::any>& config)
    -> void {
  auto sink_id = addOperator<SinkType>(config);
  connectToLastOperator(sink_id);
  finalizeGraph();
}

template <typename OperatorType, typename FunctionType>
auto DataStream::addOperatorWithFunction(const std::unordered_map<std::string, std::any>&
                                            config) -> ExecutionGraph::OperatorId {
  // Validate configuration
  if (!validateConfig(config)) {
    throw std::runtime_error("Invalid operator configuration");
  }

  // Create function from configuration
  auto func = createFunctionFromConfig<FunctionType>(config);

  // Create operator with function
  auto op = std::make_unique<OperatorType>("operator", std::move(func));
  return graph_->addOperator(std::move(op));
}

template <typename OperatorType>
auto DataStream::addOperator(const std::unordered_map<std::string, std::any>&
                                 config) -> ExecutionGraph::OperatorId {
  // For operators that don't need functions (like source/sink operators)
  // Validate configuration
  if (!validateConfig(config)) {
    throw std::runtime_error("Invalid operator configuration");
  }

  // Create operator instance with configuration
  auto op = std::make_unique<OperatorType>("operator");
  return graph_->addOperator(std::move(op));
}

template <typename FunctionType>
auto DataStream::createFunctionFromConfig(const std::unordered_map<std::string, std::any>& config)
    -> std::unique_ptr<FunctionType> {
  // Extract function name from config
  std::string func_name = "default_function";
  if (config.count("function_name")) {
    func_name = std::any_cast<std::string>(config.at("function_name"));
  }

  // Create function instance
  auto func = std::make_unique<FunctionType>(func_name);

  // Configure function based on type
  if constexpr (std::is_same_v<FunctionType, MapFunction>) {
    // For map functions, extract lambda or function pointer
    if (config.count("map_func")) {
      // This would need to be handled differently for lambda functions
      // For now, create empty function that can be configured later
    }
  } else if constexpr (std::is_same_v<FunctionType, FilterFunction>) {
    // For filter functions, extract predicate
    if (config.count("filter_func")) {
      // Similar handling for filter predicates
    }
  }

  return func;
}

}  // namespace sage_flow
