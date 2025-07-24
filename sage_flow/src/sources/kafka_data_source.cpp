#include "sources/kafka_data_source.h"
#include "message/multimodal_message.h"
#include <thread>
#include <chrono>

namespace sage_flow {

KafkaDataSource::~KafkaDataSource() {
  // Don't call virtual method in destructor
  if (!closed_) {
    cleanup_resources();
    closed_ = true;
  }
}

auto KafkaDataSource::initialize(const DataSourceConfig& config) -> bool {
  if (initialized_) {
    return true;
  }
  
  config_ = config;
  
  if (!parse_kafka_config()) {
    return false;
  }
  
  initialized_ = true;
  // Lazy initialization - don't create Kafka consumer until first use
  return true;
}

auto KafkaDataSource::has_next() -> bool {
  if (!initialized_ || closed_) {
    return false;
  }
  
  // Trigger lazy initialization on first access
  if (!consumer_active_.load()) {
    lazy_init();
  }
  
  std::lock_guard<std::mutex> lock(buffer_mutex_);
  return !message_buffer_.empty();
}

auto KafkaDataSource::next_message() -> std::unique_ptr<MultiModalMessage> {
  if (!has_next()) {
    return nullptr;
  }
  
  std::unique_lock<std::mutex> lock(buffer_mutex_);
  
  // Wait for data with timeout (similar to SAGE's pattern)
  if (message_buffer_.empty()) {
    buffer_condition_.wait_for(lock, consumer_timeout_);
  }
  
  if (message_buffer_.empty()) {
    return nullptr;
  }
  
  std::string raw_message = message_buffer_.front();
  message_buffer_.pop();
  lock.unlock();
  
  if (!raw_message.empty()) {
    std::string processed_message = deserialize_message(raw_message);
    static uint64_t uid_counter = 2000;  // Different range for Kafka messages
    return CreateTextMessage(++uid_counter, std::move(processed_message));
  }
  
  return nullptr;
}

void KafkaDataSource::close() {
  if (closed_) {
    return;
  }
  
  cleanup_resources();
  closed_ = true;
}

auto KafkaDataSource::get_config() const -> const DataSourceConfig& {
  return config_;
}

auto KafkaDataSource::is_initialized() const -> bool {
  return initialized_;
}

auto KafkaDataSource::is_closed() const -> bool {
  return closed_;
}

auto KafkaDataSource::get_kafka_stats() const -> KafkaStats {
  std::lock_guard<std::mutex> lock(buffer_mutex_);
  std::lock_guard<std::mutex> error_lock(error_mutex_);
  
  return KafkaStats{
    .topic_ = topic_,
    .group_id_ = consumer_group_,
    .consumer_active_ = consumer_active_.load(),
    .buffer_size_ = message_buffer_.size(),
    .max_buffer_size_ = buffer_size_,
    .messages_consumed_ = messages_consumed_.load(),
    .last_error_ = last_error_
  };
}

// Private methods implementing SAGE's pattern

void KafkaDataSource::lazy_init() {
  if (consumer_active_.load()) {
    return;
  }
  
  try {
    if (!create_kafka_consumer()) {
      handle_consumer_error("Failed to create Kafka consumer");
      return;
    }
    
    // Start background consumer thread (similar to SAGE's _consume_loop)
    running_.store(true);
    consumer_active_.store(true);
    
    consumer_thread_ = std::make_unique<std::thread>(&KafkaDataSource::consume_loop, this);
    
  } catch (const std::exception& e) {
    handle_consumer_error("Lazy initialization failed: " + std::string(e.what()));
  }
}

void KafkaDataSource::consume_loop() {
  // Main consumer loop similar to SAGE's KafkaSourceFunction._consume_loop
  while (running_.load()) {
    try {
      // Simulate Kafka message polling
      // In real implementation, this would poll from actual Kafka consumer
      std::this_thread::sleep_for(consumer_timeout_);
      
      // Simulate receiving messages
      static int msg_counter = 0;
      if (++msg_counter % 5 == 0) {  // Generate message every 5 iterations
        std::string simulated_message = "kafka_message_" + std::to_string(msg_counter) + 
                                       "_topic_" + topic_ + "_group_" + consumer_group_;
        
        std::unique_lock<std::mutex> lock(buffer_mutex_);
        
        // Backpressure handling (similar to SAGE's approach)
        while (message_buffer_.size() >= buffer_size_) {
          message_buffer_.pop();  // Drop oldest message
        }
        
        message_buffer_.push(std::move(simulated_message));
        ++messages_consumed_;
        
        lock.unlock();
        buffer_condition_.notify_one();
      }
      
    } catch (const std::exception& e) {
      if (running_.load()) {
        handle_consumer_error("Error in consume loop: " + std::string(e.what()));
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
      }
    }
  }
}

void KafkaDataSource::cleanup_resources() {
  running_.store(false);
  consumer_active_.store(false);
  
  // Notify waiting threads
  buffer_condition_.notify_all();
  
  if (consumer_thread_ && consumer_thread_->joinable()) {
    consumer_thread_->join();
  }
  
  consumer_thread_.reset();
  
  // Clear message buffer
  std::lock_guard<std::mutex> lock(buffer_mutex_);
  while (!message_buffer_.empty()) {
    message_buffer_.pop();
  }
}

auto KafkaDataSource::parse_kafka_config() -> bool {
  broker_list_ = config_.get_property("bootstrap_servers", "localhost:9092");
  topic_ = config_.get_property("topic", "");
  consumer_group_ = config_.get_property("group_id", "sage_consumer");
  auto_offset_reset_ = config_.get_property("auto_offset_reset", "latest");
  value_deserializer_ = config_.get_property("value_deserializer", "string");
  
  if (topic_.empty()) {
    return false;
  }
  
  // Parse numeric configurations
  try {
    std::string buffer_size_str = config_.get_property("buffer_size", "10000");
    buffer_size_ = std::stoul(buffer_size_str);
    
    std::string max_poll_str = config_.get_property("max_poll_records", "500");
    max_poll_records_ = std::stoul(max_poll_str);
    
    std::string timeout_str = config_.get_property("consumer_timeout_ms", "1000");
    consumer_timeout_ = std::chrono::milliseconds(std::stoul(timeout_str));
  } catch (const std::exception& e) {
    // Use default values on parse error
    (void)e;  // Suppress unused variable warning
  }
  
  return true;
}

auto KafkaDataSource::create_kafka_consumer() -> bool {
  // Placeholder for actual Kafka consumer creation
  // In real implementation, this would create librdkafka consumer or similar
  return true;
}

void KafkaDataSource::handle_consumer_error(const std::string& error) {
  std::lock_guard<std::mutex> lock(error_mutex_);
  last_error_ = error;
  
  // Log error (in real implementation, use proper logging)
  // consumer_active_.store(false);
}

auto KafkaDataSource::deserialize_message(const std::string& raw_message) -> std::string {
  // Implement deserialization based on value_deserializer_ setting
  if (value_deserializer_ == "json") {
    // Would parse JSON here in real implementation
    return raw_message + "_json_processed";
  }
  
  if (value_deserializer_ == "bytes") {
    // Would handle bytes conversion here in real implementation
    return raw_message + "_bytes_processed";
  }
  
  // Default case: string or unknown deserializer
  return raw_message;
}

}  // namespace sage_flow
