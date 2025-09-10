#pragma once

#include <any>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace sage_flow {

template <typename StateKey = std::string, typename StateValue = std::any>
class StateManager {
public:
  StateManager();

  auto get(const StateKey& key) -> std::optional<StateValue>;
  auto set(const StateKey& key, const StateValue& value) -> void;
  auto del(const StateKey& key) -> void;

  auto checkpoint(const std::string& checkpoint_id) -> std::string;
  auto restore(const std::string& checkpoint_id) -> bool;

  auto beginTransaction() -> void;
  auto commit() -> void;
  auto rollback() -> void;

private:
  std::unordered_map<StateKey, StateValue> state_store_;
  std::mutex mutex_;
  bool in_transaction_ = false;
  std::vector<std::pair<StateKey, std::optional<StateValue>>> transaction_log_;
};

}  // namespace sage_flow