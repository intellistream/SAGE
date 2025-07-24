#include "sources/stream_data_source.h"
#include "message/multimodal_message.h"
#include <thread>
#include <chrono>

namespace sage_flow {

StreamDataSource::~StreamDataSource() {
  // Don't call virtual method in destructor
  if (!closed_) {
    stop_streaming();
    cleanup_resources();
    closed_ = true;
  }
}

auto StreamDataSource::initialize(const DataSourceConfig& config) -> bool {
  if (initialized_) {
    return true;
  }
  
  config_ = config;
  
  // Extract configuration parameters
  stream_url_ = config_.get_property("stream_url", "");
  if (stream_url_.empty()) {
    return false;
  }
  
  // Parse buffer size
  std::string buffer_size_str = config_.get_property("buffer_size", "10000");
  try {
    buffer_size_ = std::stoul(buffer_size_str);
  } catch (const std::exception&) {
    buffer_size_ = 10000;  // Default fallback
  }
  
  initialized_ = true;
  start_streaming();
  return true;
}

auto StreamDataSource::has_next() -> bool {
  if (!initialized_ || closed_) {
    return false;
  }
  
  std::lock_guard<std::mutex> lock(buffer_mutex_);
  return !message_buffer_.empty();
}

auto StreamDataSource::next_message() -> std::unique_ptr<MultiModalMessage> {
  if (!has_next()) {
    return nullptr;
  }
  
  std::unique_lock<std::mutex> lock(buffer_mutex_);
  
  // Wait for data with timeout
  if (message_buffer_.empty()) {
    buffer_condition_.wait_for(lock, std::chrono::milliseconds(100));
  }
  
  if (message_buffer_.empty()) {
    return nullptr;
  }
  
  std::string content = message_buffer_.front();
  message_buffer_.pop();
  lock.unlock();
  
  if (!content.empty()) {
    static uint64_t uid_counter = 1000;  // Different range from file source
    return CreateTextMessage(++uid_counter, std::move(content));
  }
  
  return nullptr;
}

void StreamDataSource::close() {
  if (closed_) {
    return;
  }
  
  stop_streaming();
  cleanup_resources();
  closed_ = true;
}

auto StreamDataSource::get_config() const -> const DataSourceConfig& {
  return config_;
}

auto StreamDataSource::is_initialized() const -> bool {
  return initialized_;
}

auto StreamDataSource::is_closed() const -> bool {
  return closed_;
}

auto StreamDataSource::get_streaming_stats() const -> StreamingStats {
  std::lock_guard<std::mutex> lock(buffer_mutex_);
  return StreamingStats{
    .messages_received_ = messages_received_.load(),
    .buffer_size_ = message_buffer_.size(),
    .max_buffer_size_ = buffer_size_,
    .is_streaming_ = stream_active_.load(),
    .stream_status_ = stream_active_ ? "active" : "inactive"
  };
}

// Private methods

void StreamDataSource::start_streaming() {
  if (stream_active_.load()) {
    return;
  }
  
  running_.store(true);
  stream_active_.store(true);
  
  consumer_thread_ = std::make_unique<std::thread>(&StreamDataSource::consume_loop, this);
}

void StreamDataSource::stop_streaming() {
  if (!stream_active_.load()) {
    return;
  }
  
  running_.store(false);
  stream_active_.store(false);
  
  // Notify waiting threads
  buffer_condition_.notify_all();
  
  if (consumer_thread_ && consumer_thread_->joinable()) {
    consumer_thread_->join();
  }
}

void StreamDataSource::consume_loop() {
  while (running_.load()) {
    try {
      std::string data = read_from_stream();
      
      if (!data.empty()) {
        std::unique_lock<std::mutex> lock(buffer_mutex_);
        
        // Implement backpressure: drop oldest messages if buffer is full
        while (message_buffer_.size() >= buffer_size_) {
          message_buffer_.pop();
        }
        
        message_buffer_.push(std::move(data));
        ++messages_received_;
        
        lock.unlock();
        buffer_condition_.notify_one();
      }
      
      // Small delay to prevent CPU spinning
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
      
    } catch (const std::exception&) {
      // Log error and continue
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
  }
}

auto StreamDataSource::read_from_stream() -> std::string {
  // Placeholder implementation - would need platform-specific stream reading
  // For now, simulate streaming data
  static int counter = 0;
  
  if (++counter % 10 == 0) {  // Generate data every 10 calls
    return "simulated_stream_data_" + std::to_string(counter);
  }
  
  return "";
}

void StreamDataSource::cleanup_resources() {
  consumer_thread_.reset();
  
  std::lock_guard<std::mutex> lock(buffer_mutex_);
  while (!message_buffer_.empty()) {
    message_buffer_.pop();
  }
}

}  // namespace sage_flow
