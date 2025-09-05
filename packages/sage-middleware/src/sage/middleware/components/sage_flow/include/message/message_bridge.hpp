#pragma once

#include <atomic>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <queue>
#include <unordered_map>
#include <vector>

#include "multimodal_message.hpp"
#include "sage_packet_adapter.hpp"

namespace sage_flow {
namespace integration {

/**
 * @brief 高性能消息桥接层
 *
 * 提供 SAGE Kernel 和 sage-flow 之间的零拷贝消息转换，
 * 支持批量处理、内存池管理和异步转换。
 */
class MessageBridge {
public:
  // 转换选项配置
  struct ConversionOptions {
    bool enable_batching = true;  // 启用批量转换
    size_t batch_size = 100;      // 批量大小
    bool enable_caching = true;   // 启用结果缓存
    size_t cache_size = 1000;     // 缓存大小
    bool enable_async = false;    // 启用异步转换
    size_t thread_pool_size = 4;  // 线程池大小

    ConversionOptions() = default;
  };

  // 转换统计信息
  struct ConversionStats {
    uint64_t sage_to_flow_count{0};
    uint64_t flow_to_sage_count{0};
    uint64_t cached_conversions{0};
    uint64_t failed_conversions{0};
    double avg_conversion_time_us{0.0};

    auto reset() -> void {
      sage_to_flow_count = 0;
      flow_to_sage_count = 0;
      cached_conversions = 0;
      failed_conversions = 0;
      avg_conversion_time_us = 0.0;
    }
  };

  MessageBridge();
  explicit MessageBridge(const ConversionOptions& options);
  ~MessageBridge();

  // 禁止复制
  MessageBridge(const MessageBridge&) = delete;
  auto operator=(const MessageBridge&) -> MessageBridge& = delete;

  // 禁止移动（由于原子成员）
  MessageBridge(MessageBridge&&) = delete;
  auto operator=(MessageBridge&&) -> MessageBridge& = delete;

  // =============================================================================
  // 同步转换接口
  // =============================================================================

  /**
   * @brief SAGE 消息转换为 sage-flow 消息（同步）
   */
  auto convertToFlow(const SagePacketAdapter::SageMessage& sage_msg)
      -> std::unique_ptr<MultiModalMessage>;

  /**
   * @brief sage-flow 消息转换为 SAGE 消息（同步）
   */
  auto convertToSage(const MultiModalMessage& flow_msg)
      -> std::unique_ptr<SagePacketAdapter::SageMessage>;

  /**
   * @brief 批量转换：SAGE -> sage-flow（同步）
   */
  auto convertBatchToFlow(
      const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
          sage_msgs) -> std::vector<std::unique_ptr<MultiModalMessage>>;

  /**
   * @brief 批量转换：sage-flow -> SAGE（同步）
   */
  auto convertBatchToSage(
      const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs)
      -> std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>;

  // =============================================================================
  // 异步转换接口
  // =============================================================================

  /**
   * @brief SAGE 消息转换为 sage-flow 消息（异步）
   */
  auto convertToFlowAsync(const SagePacketAdapter::SageMessage& sage_msg)
      -> std::future<std::unique_ptr<MultiModalMessage>>;

  /**
   * @brief sage-flow 消息转换为 SAGE 消息（异步）
   */
  auto convertToSageAsync(const MultiModalMessage& flow_msg)
      -> std::future<std::unique_ptr<SagePacketAdapter::SageMessage>>;

  /**
   * @brief 批量转换：SAGE -> sage-flow（异步）
   */
  auto convertBatchToFlowAsync(
      const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
          sage_msgs)
      -> std::future<std::vector<std::unique_ptr<MultiModalMessage>>>;

  /**
   * @brief 批量转换：sage-flow -> SAGE（异步）
   */
  auto convertBatchToSageAsync(
      const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs)
      -> std::future<
          std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>>;

  // =============================================================================
  // 缓存管理
  // =============================================================================

  /**
   * @brief 清空转换缓存
   */
  auto clearCache() -> void;

  /**
   * @brief 预热缓存（预先转换常用消息）
   */
  auto warmupCache(
      const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
          sage_msgs) -> void;
  auto warmupCache(
      const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs) -> void;

  // =============================================================================
  // 配置和监控
  // =============================================================================

  /**
   * @brief 获取转换选项
   */
  auto getOptions() const -> const ConversionOptions&;

  /**
   * @brief 更新转换选项
   */
  auto updateOptions(const ConversionOptions& options) -> void;

  /**
   * @brief 获取转换统计信息
   */
  auto getStats() const -> ConversionStats;

  /**
   * @brief 重置统计信息
   */
  auto resetStats() -> void;

  /**
   * @brief 检查桥接层健康状态
   */
  auto isHealthy() const -> bool;

private:
  // 配置
  ConversionOptions options_;

  // 统计信息
  mutable ConversionStats stats_;

  // 缓存管理
  using CacheKey = std::string;  // 基于消息内容的哈希
  std::unordered_map<CacheKey, std::unique_ptr<MultiModalMessage>> flow_cache_;
  std::unordered_map<CacheKey, std::unique_ptr<SagePacketAdapter::SageMessage>>
      sage_cache_;
  mutable std::mutex cache_mutex_;

  // 异步处理
  class ThreadPool;
  std::unique_ptr<ThreadPool> thread_pool_;

  // 内部辅助方法
  auto generateCacheKey(const SagePacketAdapter::SageMessage& msg) const
      -> CacheKey;
  auto generateCacheKey(const MultiModalMessage& msg) const -> CacheKey;

  auto getCachedFlowMessage(const CacheKey& key)
      -> std::unique_ptr<MultiModalMessage>;
  auto getCachedSageMessage(const CacheKey& key)
      -> std::unique_ptr<SagePacketAdapter::SageMessage>;

  auto setCachedFlowMessage(const CacheKey& key,
                            std::unique_ptr<MultiModalMessage> msg) -> void;
  auto setCachedSageMessage(const CacheKey& key,
                            std::unique_ptr<SagePacketAdapter::SageMessage> msg)
      -> void;

  auto convertToFlowInternal(const SagePacketAdapter::SageMessage& sage_msg)
      -> std::unique_ptr<MultiModalMessage>;
  auto convertToSageInternal(const MultiModalMessage& flow_msg)
      -> std::unique_ptr<SagePacketAdapter::SageMessage>;

  auto updateConversionTime(double time_us) -> void;
  auto evictOldCacheEntries() -> void;
};

/**
 * @brief 消息桥接层的单例管理器
 *
 * 提供全局访问点和生命周期管理
 */
class MessageBridgeManager {
public:
  static auto getInstance() -> MessageBridgeManager&;

  auto getBridge() -> MessageBridge&;
  auto createBridge(const MessageBridge::ConversionOptions& options) -> void;
  auto destroyBridge() -> void;

  // 全局统计
  auto getGlobalStats() -> MessageBridge::ConversionStats;
  auto resetGlobalStats() -> void;

private:
  MessageBridgeManager() = default;
  std::unique_ptr<MessageBridge> bridge_;
  mutable std::mutex bridge_mutex_;
};

/**
 * @brief 内存池管理的消息桥接器
 *
 * 针对高频转换场景优化的特殊桥接器
 */
class PooledMessageBridge {
public:
  struct PoolConfig {
    size_t flow_message_pool_size = 1000;
    size_t sage_message_pool_size = 1000;
    bool enable_preallocation = true;
    size_t prealloc_text_messages = 500;
    size_t prealloc_binary_messages = 300;
    size_t prealloc_multimedia_messages = 200;
  };

  PooledMessageBridge();
  explicit PooledMessageBridge(const PoolConfig& config);
  ~PooledMessageBridge();

  // 池化转换接口
  auto convertToFlowPooled(const SagePacketAdapter::SageMessage& sage_msg)
      -> std::unique_ptr<MultiModalMessage>;
  auto convertToSagePooled(const MultiModalMessage& flow_msg)
      -> std::unique_ptr<SagePacketAdapter::SageMessage>;

  // 池管理
  auto preAllocateMessages() -> void;
  auto getPoolStats() -> void;
  auto resetPools() -> void;

private:
  PoolConfig config_;

  // 消息对象池
  std::queue<std::unique_ptr<MultiModalMessage>> flow_message_pool_;
  std::queue<std::unique_ptr<SagePacketAdapter::SageMessage>>
      sage_message_pool_;
  mutable std::mutex flow_pool_mutex_;
  mutable std::mutex sage_pool_mutex_;

  auto acquireFlowMessage() -> std::unique_ptr<MultiModalMessage>;
  auto releaseFlowMessage(std::unique_ptr<MultiModalMessage> msg) -> void;
  auto acquireSageMessage() -> std::unique_ptr<SagePacketAdapter::SageMessage>;
  auto releaseSageMessage(std::unique_ptr<SagePacketAdapter::SageMessage> msg)
      -> void;
};

}  // namespace integration
}  // namespace sage_flow