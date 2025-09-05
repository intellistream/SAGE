#pragma once

#include <chrono>
#include <deque>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "../window_operator.hpp"

namespace sage_flow {

class MultiModalMessage;

/**
 * @brief Session window operator for candyFlow integration
 *
 * Implements session windows that group messages by activity sessions.
 * This is a specialized component of the candyFlow streaming system, providing:
 * - Dynamic session-based windowing
 * - Configurable session timeout/gap detection
 * - Event-time and processing-time support
 * - Session key-based message grouping
 *
 * Based on candyFlow's SessionWindowOperator design with SAGE integration.
 */
class SessionWindowOperator : public WindowOperator {
public:
  /**
   * @brief Construct a session window operator
   * @param name Operator name for identification
   * @param session_timeout Maximum gap between messages in the same session
   * @param allow_late_data Whether to accept late arriving data
   */
  explicit SessionWindowOperator(std::string name,
                                 std::chrono::milliseconds session_timeout,
                                 bool allow_late_data = true);

  // Prevent copying
  SessionWindowOperator(const SessionWindowOperator&) = delete;
  auto operator=(const SessionWindowOperator&) -> SessionWindowOperator& =
                                                      delete;

  // Allow moving
  SessionWindowOperator(SessionWindowOperator&&) = default;
  auto operator=(SessionWindowOperator&&) -> SessionWindowOperator& = default;

  // WindowOperator interface implementation
  auto processWindow(
      std::vector<std::unique_ptr<MultiModalMessage>> window_messages)
      -> std::vector<std::unique_ptr<MultiModalMessage>> override;

  // SessionWindow-specific interface
  auto setSessionTimeout(std::chrono::milliseconds timeout) -> void;
  auto setWatermarkDelay(std::chrono::milliseconds delay) -> void;
  auto setMaxLateness(std::chrono::milliseconds max_lateness) -> void;
  auto enableEventTimeProcessing(bool enable) -> void;
  auto setSessionKeyExtractor(
      std::function<std::string(const MultiModalMessage&)> extractor) -> void;

  // Performance monitoring
  auto getActiveSessionCount() const -> uint64_t;
  auto getTotalSessionCount() const -> uint64_t;
  auto getLateDataCount() const -> uint64_t;
  auto getDroppedDataCount() const -> uint64_t;
  auto getAverageSessionDuration() const -> std::chrono::milliseconds;

protected:
  // Internal session management
  auto getSessionKey(const MultiModalMessage& message) -> std::string;
  auto shouldMergeSessions(const std::string& session_key,
                           uint64_t message_timestamp) -> bool;
  auto isLateData(uint64_t message_timestamp) -> bool;
  auto processLateData(std::unique_ptr<MultiModalMessage> message) -> bool;

private:
  // Session configuration
  std::chrono::milliseconds session_timeout_;
  bool allow_late_data_;
  bool event_time_processing_;
  std::function<std::string(const MultiModalMessage&)> session_key_extractor_;

  // Watermark and late data handling
  std::chrono::milliseconds watermark_delay_;
  std::chrono::milliseconds max_lateness_;
  uint64_t current_watermark_;

  // Session state management
  struct SessionState {
    std::string session_key;
    uint64_t session_start;
    uint64_t session_end;
    uint64_t last_activity;
    std::vector<std::unique_ptr<MultiModalMessage>> messages;
    bool triggered;

    SessionState(const std::string& key, uint64_t start)
        : session_key(key),
          session_start(start),
          session_end(start),
          last_activity(start),
          triggered(false) {}
  };

  std::unordered_map<std::string, SessionState> active_sessions_;

  // Performance metrics
  mutable uint64_t total_session_count_;
  mutable uint64_t late_data_count_;
  mutable uint64_t dropped_data_count_;
  mutable uint64_t total_session_duration_ms_;

  // Internal helpers
  auto findOrCreateSession(const std::string& session_key,
                           uint64_t timestamp) -> SessionState*;
  auto updateSessionActivity(SessionState& session, uint64_t timestamp) -> void;
  auto triggerExpiredSessions() -> void;
  auto emitSession(SessionState& session) -> void;
  auto cleanupTriggeredSessions() -> void;
  auto getCurrentTimestamp() -> uint64_t;
  auto updateWatermark(uint64_t message_timestamp) -> void;
  auto defaultSessionKeyExtractor(const MultiModalMessage& message)
      -> std::string;
};

}  // namespace sage_flow