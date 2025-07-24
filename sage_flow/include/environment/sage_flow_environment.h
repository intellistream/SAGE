#pragma once

#include <memory>
#include <string>
#include <unordered_map>

#include "memory/memory_pool.h"

namespace sage_flow {

// Forward declarations
class DataSource;
class DataSink;
class ProcessingFunction;

/**
 * @brief Configuration for SAGE Flow environment
 */
struct EnvironmentConfig {
  std::string job_name_;
  std::unordered_map<std::string, std::string> memory_config_;
  std::unordered_map<std::string, std::string> properties_;
  
  EnvironmentConfig() = default;
  explicit EnvironmentConfig(std::string job_name) : job_name_(std::move(job_name)) {}
};

/**
 * @brief SAGE Flow execution environment
 * 
 * This class provides the main interface for creating and executing
 * data processing pipelines in SAGE Flow, compatible with sage_core
 * DataStream API patterns.
 */
class SageFlowEnvironment {
 public:
  explicit SageFlowEnvironment(const std::string& job_name);
  explicit SageFlowEnvironment(EnvironmentConfig config);
  ~SageFlowEnvironment();

  // Prevent copying
  SageFlowEnvironment(const SageFlowEnvironment&) = delete;
  auto operator=(const SageFlowEnvironment&) -> SageFlowEnvironment& = delete;

  // Allow moving
  SageFlowEnvironment(SageFlowEnvironment&&) = default;
  auto operator=(SageFlowEnvironment&&) -> SageFlowEnvironment& = default;

  /**
   * @brief Set memory configuration for vector storage integration
   * @param config Memory configuration parameters
   */
  void set_memory(const std::unordered_map<std::string, std::string>& config);

  /**
   * @brief Set environment property
   * @param key Property key
   * @param value Property value
   */
  void set_property(const std::string& key, const std::string& value);

  /**
   * @brief Get environment property
   * @param key Property key
   * @return Property value, empty string if not found
   */
  auto get_property(const std::string& key) const -> std::string;

  /**
   * @brief Get the memory pool instance
   * @return Shared pointer to memory pool
   */
  auto get_memory_pool() -> std::shared_ptr<MemoryPool>;

  /**
   * @brief Get job name
   * @return Job name string
   */
  auto get_job_name() const -> const std::string&;

  /**
   * @brief Submit the job for execution (placeholder)
   * TODO(developer): Implement job submission when runtime is ready
   Issue URL: https://github.com/intellistream/SAGE/issues/349
   */
  void submit();

  /**
   * @brief Close the environment and cleanup resources
   */
  void close();

  /**
   * @brief Run in streaming mode (placeholder)
   * TODO(developer): Implement streaming execution when runtime is ready
   Issue URL: https://github.com/intellistream/SAGE/issues/348
   */
  void run_streaming();

  /**
   * @brief Run in batch mode (placeholder)
   * TODO(developer): Implement batch execution when runtime is ready
   Issue URL: https://github.com/intellistream/SAGE/issues/347
   */
  void run_batch();

 private:
  EnvironmentConfig config_;
  std::shared_ptr<MemoryPool> memory_pool_;
  bool is_closed_ = false;
};

}  // namespace sage_flow
