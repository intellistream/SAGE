#include "environment/sage_flow_environment.h"

#include <iostream>

namespace sage_flow {

SageFlowEnvironment::SageFlowEnvironment(const std::string& job_name)
    : config_(job_name), memory_pool_(CreateDefaultMemoryPool()) {}

SageFlowEnvironment::SageFlowEnvironment(EnvironmentConfig config)
    : config_(std::move(config)), memory_pool_(CreateDefaultMemoryPool()) {}

SageFlowEnvironment::~SageFlowEnvironment() {
  if (!is_closed_) {
    close();
  }
}

void SageFlowEnvironment::set_memory(const std::unordered_map<std::string, std::string>& config) {
  config_.memory_config_ = config;
  // TODO(developer): Configure memory pool based on settings
  // Issue URL: https://github.com/intellistream/SAGE/issues/355
}

void SageFlowEnvironment::set_property(const std::string& key, const std::string& value) {
  config_.properties_[key] = value;
}

auto SageFlowEnvironment::get_property(const std::string& key) const -> std::string {
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
  // TODO(developer): Implement job submission logic
  // Issue URL: https://github.com/intellistream/SAGE/issues/354
  std::cout << "[SAGE Flow] Job '" << config_.job_name_ << "' submitted for execution\n";
}

void SageFlowEnvironment::close() {
  if (!is_closed_) {
    // TODO(developer): Cleanup resources, stop running jobs
    // Issue URL: https://github.com/intellistream/SAGE/issues/353
    if (memory_pool_) {
      memory_pool_->reset();
    }
    std::cout << "[SAGE Flow] Environment '" << config_.job_name_ << "' closed\n";
    is_closed_ = true;
  }
}

void SageFlowEnvironment::run_streaming() {
  // TODO(developer): Implement streaming execution
  // Issue URL: https://github.com/intellistream/SAGE/issues/352
  std::cout << "[SAGE Flow] Starting streaming execution for job '" << config_.job_name_ << "'\n";
}

void SageFlowEnvironment::run_batch() {
  // TODO(developer): Implement batch execution
  // Issue URL: https://github.com/intellistream/SAGE/issues/351
  std::cout << "[SAGE Flow] Starting batch execution for job '" << config_.job_name_ << "'\n";
}

}  // namespace sage_flow
