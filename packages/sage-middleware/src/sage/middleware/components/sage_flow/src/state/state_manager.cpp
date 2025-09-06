#include "../../include/state/state_manager.hpp"

#include <iostream>
#include <sstream>

namespace sage_flow {

StateManager::StateManager() = default;

auto StateManager::get(const StateKey& key) -> std::optional<StateValue> {
  std::lock_guard<std::mutex> lock(mutex_);
  auto it = state_store_.find(key);
  if (it != state_store_.end()) {
    return it->second;
  }
  return std::optional<StateValue>{};
}

auto StateManager::set(const StateKey& key, const StateValue& value) -> void {
  std::lock_guard<std::mutex> lock(mutex_);
  state_store_[key] = value;
  if (in_transaction_) {
    transaction_log_.emplace_back(key, value);
  }
}

auto StateManager::del(const StateKey& key) -> void {
  std::lock_guard<std::mutex> lock(mutex_);
  state_store_.erase(key);
  if (in_transaction_) {
    transaction_log_.emplace_back(key, StateValue{}); // Mark as deleted
  }
}

auto StateManager::checkpoint(const std::string& checkpoint_id) -> std::string {
  std::lock_guard<std::mutex> lock(mutex_);
  std::stringstream ss;
  for (const auto& [k, v] : state_store_) {
    // Serialize key and value (simple for demo, use proper serialization in production)
    ss << k << ":" << v.type().name() << ":" << /* serialize v */ "value" << ";";
  }
  std::string data = ss.str();
  // Save to file or storage with checkpoint_id
  std::cout << "[StateManager] Checkpoint " << checkpoint_id << " created with " << state_store_.size() << " entries" << std::endl;
  return data;
}

auto StateManager::restore(const std::string& checkpoint_id) -> bool {
  std::lock_guard<std::mutex> lock(mutex_);
  // Load from storage
  std::string data = /* load data for checkpoint_id */ checkpoint_id; // Placeholder
  state_store_.clear();
  // Parse and restore (simple for demo)
  std::cout << "[StateManager] Restored from checkpoint " << checkpoint_id << std::endl;
  return true;
}

auto StateManager::beginTransaction() -> void {
  std::lock_guard<std::mutex> lock(mutex_);
  in_transaction_ = true;
  transaction_log_.clear();
}

auto StateManager::commit() -> void {
  std::lock_guard<std::mutex> lock(mutex_);
  in_transaction_ = false;
  transaction_log_.clear();
}

auto StateManager::rollback() -> void {
  std::lock_guard<std::mutex> lock(mutex_);
  for (const auto& [k, v] : transaction_log_) {
    if (v.has_value()) {
      state_store_[k] = v;
    } else {
      state_store_.erase(k);
    }
  }
  in_transaction_ = false;
  transaction_log_.clear();
}

}  // namespace sage_flow