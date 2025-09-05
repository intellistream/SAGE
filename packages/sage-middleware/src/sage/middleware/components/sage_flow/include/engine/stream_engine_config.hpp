#pragma once

#include <chrono>
#include <cstddef>
#include <string>

#include "stream_engine_enums.hpp"

namespace sage_flow {

/**
 * @brief Configuration for the stream engine
 */
struct EngineConfig {
  ExecutionMode execution_mode = ExecutionMode::MULTI_THREADED;
  ExecutionStrategy execution_strategy = ExecutionStrategy::STREAMING;
  size_t thread_pool_size = 4;
  size_t max_queue_size = 10000;
  size_t batch_size = 100;
  std::chrono::milliseconds timeout = std::chrono::milliseconds(30000);
  bool enable_checkpointing = false;
  bool enable_fault_tolerance = true;
  bool enable_sage_compatibility = true;
  std::string checkpoint_directory = "./checkpoints";
};

}  // namespace sage_flow