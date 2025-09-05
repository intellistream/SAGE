#include "message/message_bridge.hpp"

#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <thread>

namespace sage_flow {
namespace integration {

// =============================================================================
// ThreadPool 实现（内部类）
// =============================================================================

class MessageBridge::ThreadPool {
public:
  explicit ThreadPool(size_t num_threads) : stop_(false) {
    for (size_t i = 0; i < num_threads; ++i) {
      workers_.emplace_back([this] {
        for (;;) {
          std::function<void()> task;
          {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            condition_.wait(lock, [this] { return stop_ || !tasks_.empty(); });

            if (stop_ && tasks_.empty()) {
              return;
            }

            task = std::move(tasks_.front());
            tasks_.pop();
          }
          task();
        }
      });
    }
  }

  ~ThreadPool() {
    {
      std::unique_lock<std::mutex> lock(queue_mutex_);
      stop_ = true;
    }

    condition_.notify_all();

    for (std::thread& worker : workers_) {
      worker.join();
    }
  }

  template <class F, class... Args>
  auto enqueue(F&& f, Args&&... args)
      -> std::future<typename std::result_of<F(Args...)>::type> {
    using return_type = typename std::result_of<F(Args...)>::type;

    auto task = std::make_shared<std::packaged_task<return_type()>>(
        std::bind(std::forward<F>(f), std::forward<Args>(args)...));

    std::future<return_type> res = task->get_future();

    {
      std::unique_lock<std::mutex> lock(queue_mutex_);

      if (stop_) {
        throw std::runtime_error("enqueue on stopped ThreadPool");
      }

      tasks_.emplace([task]() { (*task)(); });
    }

    condition_.notify_one();
    return res;
  }

private:
  std::vector<std::thread> workers_;
  std::queue<std::function<void()>> tasks_;
  std::mutex queue_mutex_;
  std::condition_variable condition_;
  bool stop_;
};

// =============================================================================
// MessageBridge 实现
// =============================================================================

MessageBridge::MessageBridge() : options_() {
  if (options_.enable_async) {
    thread_pool_ = std::make_unique<ThreadPool>(options_.thread_pool_size);
  }
}

MessageBridge::MessageBridge(const ConversionOptions& options)
    : options_(options) {
  if (options_.enable_async) {
    thread_pool_ = std::make_unique<ThreadPool>(options_.thread_pool_size);
  }
}

MessageBridge::~MessageBridge() = default;

auto MessageBridge::convertToFlow(
    const SagePacketAdapter::SageMessage& sage_msg)
    -> std::unique_ptr<MultiModalMessage> {
  auto start_time = std::chrono::high_resolution_clock::now();

  try {
    // 检查缓存
    if (options_.enable_caching) {
      auto cache_key = generateCacheKey(sage_msg);
      if (auto cached = getCachedFlowMessage(cache_key)) {
        stats_.cached_conversions++;
        return cached;
      }
    }

    // 执行转换
    auto result = convertToFlowInternal(sage_msg);

    // 缓存结果
    if (options_.enable_caching && result) {
      auto cache_key = generateCacheKey(sage_msg);
      setCachedFlowMessage(cache_key,
                           std::unique_ptr<MultiModalMessage>(result.get()));
    }

    stats_.sage_to_flow_count++;

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        end_time - start_time);
    updateConversionTime(static_cast<double>(duration.count()));

    return result;

  } catch (const std::exception& e) {
    stats_.failed_conversions++;
    std::cerr << "MessageBridge::convertToFlow failed: " << e.what()
              << std::endl;
    return nullptr;
  }
}

auto MessageBridge::convertToSage(const MultiModalMessage& flow_msg)
    -> std::unique_ptr<SagePacketAdapter::SageMessage> {
  auto start_time = std::chrono::high_resolution_clock::now();

  try {
    // 检查缓存
    if (options_.enable_caching) {
      auto cache_key = generateCacheKey(flow_msg);
      if (auto cached = getCachedSageMessage(cache_key)) {
        stats_.cached_conversions++;
        return cached;
      }
    }

    // 执行转换
    auto result = convertToSageInternal(flow_msg);

    // 缓存结果
    if (options_.enable_caching && result) {
      auto cache_key = generateCacheKey(flow_msg);
      setCachedSageMessage(
          cache_key,
          std::unique_ptr<SagePacketAdapter::SageMessage>(result.get()));
    }

    stats_.flow_to_sage_count++;

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        end_time - start_time);
    updateConversionTime(static_cast<double>(duration.count()));

    return result;

  } catch (const std::exception& e) {
    stats_.failed_conversions++;
    std::cerr << "MessageBridge::convertToSage failed: " << e.what()
              << std::endl;
    return nullptr;
  }
}

auto MessageBridge::convertBatchToFlow(
    const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
        sage_msgs) -> std::vector<std::unique_ptr<MultiModalMessage>> {
  std::vector<std::unique_ptr<MultiModalMessage>> results;
  results.reserve(sage_msgs.size());

  if (options_.enable_batching && sage_msgs.size() >= options_.batch_size) {
    // 批量处理模式
    for (const auto& sage_msg : sage_msgs) {
      if (sage_msg) {
        results.push_back(convertToFlow(*sage_msg));
      }
    }
  } else {
    // 单个处理模式
    for (const auto& sage_msg : sage_msgs) {
      if (sage_msg) {
        results.push_back(convertToFlow(*sage_msg));
      }
    }
  }

  return results;
}

auto MessageBridge::convertBatchToSage(
    const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs)
    -> std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>> {
  std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>> results;
  results.reserve(flow_msgs.size());

  if (options_.enable_batching && flow_msgs.size() >= options_.batch_size) {
    // 批量处理模式
    for (const auto& flow_msg : flow_msgs) {
      if (flow_msg) {
        results.push_back(convertToSage(*flow_msg));
      }
    }
  } else {
    // 单个处理模式
    for (const auto& flow_msg : flow_msgs) {
      if (flow_msg) {
        results.push_back(convertToSage(*flow_msg));
      }
    }
  }

  return results;
}

// =============================================================================
// 异步转换接口
// =============================================================================

auto MessageBridge::convertToFlowAsync(
    const SagePacketAdapter::SageMessage& sage_msg)
    -> std::future<std::unique_ptr<MultiModalMessage>> {
  if (!thread_pool_) {
    // 如果没有线程池，回退到同步模式
    std::promise<std::unique_ptr<MultiModalMessage>> promise;
    auto future = promise.get_future();
    promise.set_value(convertToFlow(sage_msg));
    return future;
  }

  return thread_pool_->enqueue(
      [this, &sage_msg]() { return convertToFlow(sage_msg); });
}

auto MessageBridge::convertToSageAsync(const MultiModalMessage& flow_msg)
    -> std::future<std::unique_ptr<SagePacketAdapter::SageMessage>> {
  if (!thread_pool_) {
    // 如果没有线程池，回退到同步模式
    std::promise<std::unique_ptr<SagePacketAdapter::SageMessage>> promise;
    auto future = promise.get_future();
    promise.set_value(convertToSage(flow_msg));
    return future;
  }

  return thread_pool_->enqueue(
      [this, &flow_msg]() { return convertToSage(flow_msg); });
}

auto MessageBridge::convertBatchToFlowAsync(
    const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
        sage_msgs)
    -> std::future<std::vector<std::unique_ptr<MultiModalMessage>>> {
  if (!thread_pool_) {
    // 如果没有线程池，回退到同步模式
    std::promise<std::vector<std::unique_ptr<MultiModalMessage>>> promise;
    auto future = promise.get_future();
    promise.set_value(convertBatchToFlow(sage_msgs));
    return future;
  }

  return thread_pool_->enqueue(
      [this, &sage_msgs]() { return convertBatchToFlow(sage_msgs); });
}

auto MessageBridge::convertBatchToSageAsync(
    const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs)
    -> std::future<
        std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>> {
  if (!thread_pool_) {
    // 如果没有线程池，回退到同步模式
    std::promise<std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>>
        promise;
    auto future = promise.get_future();
    promise.set_value(convertBatchToSage(flow_msgs));
    return future;
  }

  return thread_pool_->enqueue(
      [this, &flow_msgs]() { return convertBatchToSage(flow_msgs); });
}

// =============================================================================
// 缓存管理
// =============================================================================

auto MessageBridge::clearCache() -> void {
  std::lock_guard<std::mutex> lock(cache_mutex_);
  flow_cache_.clear();
  sage_cache_.clear();
}

auto MessageBridge::warmupCache(
    const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
        sage_msgs) -> void {
  for (const auto& msg : sage_msgs) {
    if (msg) {
      convertToFlow(*msg);  // 这会自动缓存结果
    }
  }
}

auto MessageBridge::warmupCache(
    const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs) -> void {
  for (const auto& msg : flow_msgs) {
    if (msg) {
      convertToSage(*msg);  // 这会自动缓存结果
    }
  }
}

// =============================================================================
// 配置和监控
// =============================================================================

auto MessageBridge::getOptions() const -> const ConversionOptions& {
  return options_;
}

auto MessageBridge::updateOptions(const ConversionOptions& options) -> void {
  options_ = options;

  // 如果异步选项改变，重新创建线程池
  if (options_.enable_async && !thread_pool_) {
    thread_pool_ = std::make_unique<ThreadPool>(options_.thread_pool_size);
  } else if (!options_.enable_async && thread_pool_) {
    thread_pool_.reset();
  }
}

auto MessageBridge::getStats() const -> ConversionStats { return stats_; }

auto MessageBridge::resetStats() -> void { stats_.reset(); }

auto MessageBridge::isHealthy() const -> bool {
  // 简单的健康检查
  return stats_.failed_conversions < 100;  // 允许少量失败
}

// =============================================================================
// 私有辅助方法
// =============================================================================

auto MessageBridge::generateCacheKey(
    const SagePacketAdapter::SageMessage& msg) const -> CacheKey {
  std::ostringstream oss;
  oss << msg.getUid() << ":" << static_cast<int>(msg.getContentType()) << ":"
      << std::hash<std::string>{}(msg.getContentAsString());
  return oss.str();
}

auto MessageBridge::generateCacheKey(const MultiModalMessage& msg) const
    -> CacheKey {
  std::ostringstream oss;
  oss << msg.getUid() << ":" << static_cast<int>(msg.getContentType()) << ":"
      << msg.getTimestamp();
  return oss.str();
}

auto MessageBridge::getCachedFlowMessage(const CacheKey& key)
    -> std::unique_ptr<MultiModalMessage> {
  std::lock_guard<std::mutex> lock(cache_mutex_);
  auto it = flow_cache_.find(key);
  if (it != flow_cache_.end()) {
    // 创建副本返回
    return std::unique_ptr<MultiModalMessage>(it->second.get());
  }
  return nullptr;
}

auto MessageBridge::getCachedSageMessage(const CacheKey& key)
    -> std::unique_ptr<SagePacketAdapter::SageMessage> {
  std::lock_guard<std::mutex> lock(cache_mutex_);
  auto it = sage_cache_.find(key);
  if (it != sage_cache_.end()) {
    // 创建副本返回
    return it->second->clone();
  }
  return nullptr;
}

auto MessageBridge::setCachedFlowMessage(
    const CacheKey& key, std::unique_ptr<MultiModalMessage> msg) -> void {
  std::lock_guard<std::mutex> lock(cache_mutex_);

  // 检查缓存大小
  if (flow_cache_.size() >= options_.cache_size) {
    evictOldCacheEntries();
  }

  flow_cache_[key] = std::move(msg);
}

auto MessageBridge::setCachedSageMessage(
    const CacheKey& key,
    std::unique_ptr<SagePacketAdapter::SageMessage> msg) -> void {
  std::lock_guard<std::mutex> lock(cache_mutex_);

  // 检查缓存大小
  if (sage_cache_.size() >= options_.cache_size) {
    evictOldCacheEntries();
  }

  sage_cache_[key] = std::move(msg);
}

auto MessageBridge::convertToFlowInternal(
    const SagePacketAdapter::SageMessage& sage_msg)
    -> std::unique_ptr<MultiModalMessage> {
  return MessageConverter::convertToMultiModal(sage_msg);
}

auto MessageBridge::convertToSageInternal(const MultiModalMessage& flow_msg)
    -> std::unique_ptr<SagePacketAdapter::SageMessage> {
  return MessageConverter::convertFromMultiModal(flow_msg);
}

auto MessageBridge::updateConversionTime(double time_us) -> void {
  // 简单的移动平均
  double current_avg = stats_.avg_conversion_time_us;
  double new_avg = (current_avg * 0.9) + (time_us * 0.1);
  stats_.avg_conversion_time_us = new_avg;
}

auto MessageBridge::evictOldCacheEntries() -> void {
  // 简单的 LRU 模拟：删除一半的条目
  auto flow_it = flow_cache_.begin();
  std::advance(flow_it, flow_cache_.size() / 2);
  flow_cache_.erase(flow_cache_.begin(), flow_it);

  auto sage_it = sage_cache_.begin();
  std::advance(sage_it, sage_cache_.size() / 2);
  sage_cache_.erase(sage_cache_.begin(), sage_it);
}

// =============================================================================
// MessageBridgeManager 实现
// =============================================================================

auto MessageBridgeManager::getInstance() -> MessageBridgeManager& {
  static MessageBridgeManager instance;
  return instance;
}

auto MessageBridgeManager::getBridge() -> MessageBridge& {
  std::lock_guard<std::mutex> lock(bridge_mutex_);

  if (!bridge_) {
    bridge_ = std::make_unique<MessageBridge>();
  }

  return *bridge_;
}

auto MessageBridgeManager::createBridge(
    const MessageBridge::ConversionOptions& options) -> void {
  std::lock_guard<std::mutex> lock(bridge_mutex_);
  bridge_ = std::make_unique<MessageBridge>(options);
}

auto MessageBridgeManager::destroyBridge() -> void {
  std::lock_guard<std::mutex> lock(bridge_mutex_);
  bridge_.reset();
}

auto MessageBridgeManager::getGlobalStats() -> MessageBridge::ConversionStats {
  std::lock_guard<std::mutex> lock(bridge_mutex_);

  if (bridge_) {
    return bridge_->getStats();
  }

  return MessageBridge::ConversionStats{};
}

auto MessageBridgeManager::resetGlobalStats() -> void {
  std::lock_guard<std::mutex> lock(bridge_mutex_);

  if (bridge_) {
    bridge_->resetStats();
  }
}

}  // namespace integration
}  // namespace sage_flow