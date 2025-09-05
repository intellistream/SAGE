#pragma once

#include <cstdint>

namespace sage_flow {

/**
 * @brief Execution modes for the stream engine
 */
enum class ExecutionMode : std::uint8_t {
  SINGLE_THREADED = 0,
  MULTI_THREADED = 1,
  ASYNC = 2,
  DISTRIBUTED = 3,  // SAGE compatible distributed mode
  HYBRID = 4        // Hybrid Python/C++ execution mode
};

/**
 * @brief States for execution graphs
 */
enum class GraphState : std::uint8_t {
  UNKNOWN = 0,
  SUBMITTED = 1,
  RUNNING = 2,
  COMPLETED = 3,
  STOPPED = 4,
  ERROR = 5,
  PAUSED = 6,     // Paused state
  RECOVERING = 7  // Recovery state
};

/**
 * @brief Execution strategies compatible with SAGE
 */
enum class ExecutionStrategy : std::uint8_t {
  EAGER = 0,      // Immediate execution
  LAZY = 1,       // Lazy loading execution
  STREAMING = 2,  // Streaming execution
  BATCH = 3,      // Batch processing execution
  ADAPTIVE = 4    // Adaptive execution
};

}  // namespace sage_flow