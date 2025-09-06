#include "environment/sage_flow_environment.hpp"

#include <iostream>

#include "data_stream/data_stream.hpp"
#include "../../include/message/multimodal_message.hpp"
#include "engine/execution_graph.hpp"
#include "engine/stream_engine.hpp"
#include "memory/memory_pool.hpp"
#include "message/multimodal_message.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

SageFlowEnvironment::SageFlowEnvironment(const std::string& job_name)
    : config_(job_name),
      memory_pool_(CreateDefaultMemoryPool()),
      stream_engine_(std::make_shared<StreamEngine>()),
      execution_graph_(std::make_shared<ExecutionGraph>()) {}

SageFlowEnvironment::SageFlowEnvironment(EnvironmentConfig config)
    : config_(std::move(config)),
      memory_pool_(CreateDefaultMemoryPool()),
      stream_engine_(std::make_shared<StreamEngine>()),
      execution_graph_(std::make_shared<ExecutionGraph>()) {}

SageFlowEnvironment::~SageFlowEnvironment() {
  if (!is_closed_) {
    close();
  }
}

void SageFlowEnvironment::set_memory(
    const std::unordered_map<std::string, std::string>& config) {
  config_.memory_config_ = config;
  // TODO(developer): Configure memory pool based on settings
  // Issue URL: https://github.com/intellistream/SAGE/issues/355
}

void SageFlowEnvironment::set_property(const std::string& key,
                                       const std::string& value) {
  config_.properties_[key] = value;
}

auto SageFlowEnvironment::get_property(const std::string& key) const
    -> std::string {
  auto it = config_.properties_.find(key);
  return (it != config_.properties_.end()) ? it->second : "";
}

auto SageFlowEnvironment::get_memory_pool() -> std::shared_ptr<MemoryPool> {
  return memory_pool_;
}

auto SageFlowEnvironment::get_job_name() const -> const std::string& {
  return config_.job_name_;
}

void SageFlowEnvironment::submit() {
  try {
    // Validate environment state
    if (config_.job_name_.empty()) {
      throw std::runtime_error("Job name cannot be empty");
    }

    if (is_closed_) {
      throw std::runtime_error("Environment is already closed");
    }

    // Validate execution components
    if (!stream_engine_) {
      throw std::runtime_error("Stream engine not initialized");
    }

    if (!execution_graph_) {
      throw std::runtime_error("Execution graph not initialized");
    }

    // TODO(developer): Add actual job submission logic when runtime is ready
    // Issue URL: https://github.com/intellistream/SAGE/issues/354

    std::cout << "[SAGE Flow] Job '" << config_.job_name_
              << "' submitted for execution\n";

  } catch (const std::exception& e) {
    std::cerr << "[SAGE Flow] Failed to submit job '" << config_.job_name_
              << "': " << e.what() << "\n";
    throw;
  }
}

void SageFlowEnvironment::close() {
  if (!is_closed_) {
    try {
      // Stop any running execution
      // TODO(developer): Implement proper job cancellation and cleanup
      // Issue URL: https://github.com/intellistream/SAGE/issues/353

      // Cleanup memory pool
      if (memory_pool_) {
        memory_pool_->reset();
      }

      // Cleanup execution components
      if (stream_engine_) {
        // TODO: Add proper shutdown logic when StreamEngine interface is defined
      }

      if (execution_graph_) {
        // TODO: Add proper cleanup logic when ExecutionGraph interface is defined
      }

      std::cout << "[SAGE Flow] Environment '" << config_.job_name_
                << "' closed successfully\n";
      is_closed_ = true;

    } catch (const std::exception& e) {
      std::cerr << "[SAGE Flow] Error during environment cleanup: "
                << e.what() << "\n";
      is_closed_ = true;  // Mark as closed even if cleanup failed
      throw;
    }
  }
}

void SageFlowEnvironment::run_streaming() {
  try {
    if (is_closed_) {
      throw std::runtime_error("Environment is closed");
    }

    if (!stream_engine_) {
      throw std::runtime_error("Stream engine not available");
    }

    // TODO(developer): Implement actual streaming execution logic
    // Issue URL: https://github.com/intellistream/SAGE/issues/352
    // This should start the streaming pipeline and handle continuous data processing

    std::cout << "[SAGE Flow] Starting streaming execution for job '"
              << config_.job_name_ << "'\n";

  } catch (const std::exception& e) {
    std::cerr << "[SAGE Flow] Failed to start streaming execution: "
              << e.what() << "\n";
    throw;
  }
}

void SageFlowEnvironment::run_batch() {
  try {
    if (is_closed_) {
      throw std::runtime_error("Environment is closed");
    }

    if (!execution_graph_) {
      throw std::runtime_error("Execution graph not available");
    }

    // TODO(developer): Implement actual batch execution logic
    // Issue URL: https://github.com/intellistream/SAGE/issues/351
    // This should process all available data in batch mode and then complete

    std::cout << "[SAGE Flow] Starting batch execution for job '"
              << config_.job_name_ << "'\n";

  } catch (const std::exception& e) {
    std::cerr << "[SAGE Flow] Failed to start batch execution: "
              << e.what() << "\n";
    throw;
  }
}

auto SageFlowEnvironment::create_datastream() -> DataStream<MultiModalMessage> {
   // Create a new execution graph for this datastream
   auto graph = std::make_shared<ExecutionGraph>();
   return {stream_engine_, graph, static_cast<ExecutionGraph::OperatorId>(-1)};
}

// ===============================
// Python-friendly method implementations
// ===============================

auto SageFlowEnvironment::get_config() const -> std::unordered_map<std::string, std::string> {
    std::unordered_map<std::string, std::string> config_map;

    // Add basic configuration
    config_map["job_name"] = config_.job_name_;

    // Add memory configuration
    for (const auto& [key, value] : config_.memory_config_) {
        config_map["memory_" + key] = value;
    }

    // Add properties
    for (const auto& [key, value] : config_.properties_) {
        config_map["property_" + key] = value;
    }

    return config_map;
}

auto SageFlowEnvironment::is_ready() const -> bool {
    return !is_closed_ &&
           stream_engine_ != nullptr &&
           execution_graph_ != nullptr &&
           !config_.job_name_.empty();
}

auto SageFlowEnvironment::get_status() const -> std::unordered_map<std::string, std::string> {
    std::unordered_map<std::string, std::string> status;

    status["job_name"] = config_.job_name_;
    status["is_closed"] = is_closed_ ? "true" : "false";
    status["has_stream_engine"] = (stream_engine_ != nullptr) ? "true" : "false";
    status["has_execution_graph"] = (execution_graph_ != nullptr) ? "true" : "false";
    status["has_memory_pool"] = (memory_pool_ != nullptr) ? "true" : "false";

    return status;
}

}  // namespace sage_flow
