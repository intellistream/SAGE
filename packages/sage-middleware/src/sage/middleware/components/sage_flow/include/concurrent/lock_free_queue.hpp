#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <mutex>
#include <thread>
#include <type_traits>
#include <vector>

namespace sage_flow {

/**
 * @brief Lock-free queue implementation for candyFlow integration
 *
 * Implements a high-performance, lock-free MPMC (Multi-Producer Multi-Consumer)
 * queue. This is a critical component of the candyFlow streaming system,
 * providing:
 * - Wait-free enqueue and dequeue operations
 * - ABA problem prevention using hazard pointers
 * - Memory-efficient circular buffer design
 * - NUMA-aware memory layout optimization
 *
 * Based on candyFlow's LockFreeQueue design with SAGE integration.
 *
 * @tparam T The type of elements stored in the queue
 */
template <typename T>
class LockFreeQueue {
private:
  static_assert(std::is_move_constructible_v<T>,
                "T must be move constructible");
  static_assert(std::is_move_assignable_v<T>, "T must be move assignable");

  // Node structure for the queue
  struct Node {
    std::atomic<T*> data{nullptr};
    std::atomic<Node*> next{nullptr};

    Node() = default;
    explicit Node(T* item) : data(item) {}
  };

  // Hazard pointer structure for memory management
  struct HazardPointer {
    std::atomic<Node*> pointer{nullptr};
    std::atomic<std::thread::id> owner{std::thread::id{}};
  };

  // Thread-local storage for performance optimization
  struct ThreadLocalData {
    Node* cached_nodes[32];
    size_t cached_count{0};
    HazardPointer* hazard_ptr{nullptr};
  };

public:
  /**
   * @brief Construct a lock-free queue
   * @param initial_capacity Initial capacity hint (for memory pre-allocation)
   */
  explicit LockFreeQueue(size_t initial_capacity = 1024);

  /**
   * @brief Destructor
   */
  ~LockFreeQueue();

  // Prevent copying
  LockFreeQueue(const LockFreeQueue&) = delete;
  auto operator=(const LockFreeQueue&) -> LockFreeQueue& = delete;

  // Allow moving
  LockFreeQueue(LockFreeQueue&& other) noexcept;
  auto operator=(LockFreeQueue&& other) noexcept -> LockFreeQueue&;

  /**
   * @brief Enqueue an element (wait-free)
   * @param item Element to enqueue
   * @return true if successful, false if queue is full or closed
   */
  auto enqueue(T item) -> bool;

  /**
   * @brief Try to enqueue an element (wait-free)
   * @param item Element to enqueue
   * @return true if successful, false if would block or queue is closed
   */
  auto try_enqueue(T item) -> bool;

  /**
   * @brief Enqueue an element with timeout
   * @param item Element to enqueue
   * @param timeout Maximum time to wait
   * @return true if successful, false if timeout or queue is closed
   */
  template <typename Rep, typename Period>
  auto enqueue_for(T item,
                   const std::chrono::duration<Rep, Period>& timeout) -> bool;

  /**
   * @brief Dequeue an element (wait-free)
   * @param item Reference to store the dequeued element
   * @return true if successful, false if queue is empty or closed
   */
  auto dequeue(T& item) -> bool;

  /**
   * @brief Try to dequeue an element (wait-free)
   * @param item Reference to store the dequeued element
   * @return true if successful, false if would block or queue is empty
   */
  auto try_dequeue(T& item) -> bool;

  /**
   * @brief Dequeue an element with timeout
   * @param item Reference to store the dequeued element
   * @param timeout Maximum time to wait
   * @return true if successful, false if timeout or queue is empty
   */
  template <typename Rep, typename Period>
  auto dequeue_for(T& item,
                   const std::chrono::duration<Rep, Period>& timeout) -> bool;

  /**
   * @brief Dequeue multiple elements (bulk operation)
   * @param items Vector to store dequeued elements
   * @param max_count Maximum number of elements to dequeue
   * @return Number of elements actually dequeued
   */
  auto dequeue_bulk(std::vector<T>& items, size_t max_count) -> size_t;

  /**
   * @brief Enqueue multiple elements (bulk operation)
   * @param items Vector of elements to enqueue
   * @return Number of elements actually enqueued
   */
  auto enqueue_bulk(const std::vector<T>& items) -> size_t;

  // Queue state queries
  auto size() const -> size_t;
  auto empty() const -> bool;
  auto full() const -> bool;
  auto capacity() const -> size_t;

  // Queue management
  auto clear() -> void;
  auto close() -> void;
  auto is_closed() const -> bool;
  auto reserve(size_t new_capacity) -> bool;

  // Performance monitoring
  auto get_enqueue_count() const -> uint64_t;
  auto get_dequeue_count() const -> uint64_t;
  auto get_contention_count() const -> uint64_t;
  auto get_memory_usage() const -> size_t;
  auto reset_statistics() -> void;

  // Advanced operations
  auto peek(T& item) const -> bool;  // Look at front element without removing
  auto peek_back(T& item) const
      -> bool;                    // Look at back element without removing
  auto wait_for_space() -> void;  // Wait until space is available
  auto wait_for_data() -> void;   // Wait until data is available

private:
  // Queue pointers
  alignas(64) std::atomic<Node*> head_{nullptr};  // Cache line alignment
  alignas(64) std::atomic<Node*> tail_{nullptr};

  // Queue state
  std::atomic<size_t> size_{0};
  std::atomic<size_t> capacity_;
  std::atomic<bool> closed_{false};

  // Performance counters
  mutable std::atomic<uint64_t> enqueue_count_{0};
  mutable std::atomic<uint64_t> dequeue_count_{0};
  mutable std::atomic<uint64_t> contention_count_{0};

  // Hazard pointer management
  static constexpr size_t MAX_HAZARD_POINTERS = 128;
  HazardPointer hazard_pointers_[MAX_HAZARD_POINTERS];
  std::atomic<size_t> hazard_pointer_count_{0};

  // Memory management
  std::atomic<Node*> free_list_{nullptr};
  static thread_local ThreadLocalData thread_data_;

  // Condition variables for blocking operations (fallback)
  mutable std::mutex wait_mutex_;
  mutable std::condition_variable space_available_;
  mutable std::condition_variable data_available_;

  // Internal helper methods
  auto allocate_node() -> Node*;
  auto deallocate_node(Node* node) -> void;
  auto acquire_hazard_pointer() -> HazardPointer*;
  auto release_hazard_pointer(HazardPointer* hp) -> void;
  auto is_hazardous(Node* node) -> bool;
  auto retire_node(Node* node) -> void;
  auto reclaim_nodes() -> void;

  // Memory ordering helpers
  auto load_head(std::memory_order order = std::memory_order_acquire) const
      -> Node*;
  auto load_tail(std::memory_order order = std::memory_order_acquire) const
      -> Node*;
  auto compare_exchange_head(Node*& expected, Node* desired) -> bool;
  auto compare_exchange_tail(Node*& expected, Node* desired) -> bool;

  // Performance optimization
  auto prefetch_node(Node* node) const -> void;
  auto optimize_memory_layout() -> void;
  auto get_numa_node() const -> int;

  // Statistics helpers
  auto increment_enqueue_count() const -> void;
  auto increment_dequeue_count() const -> void;
  auto increment_contention_count() const -> void;
};

/**
 * @brief Specialized lock-free queue for pointers
 *
 * Optimized version for pointer types with reduced memory overhead.
 */
template <typename T>
class LockFreePointerQueue {
public:
  explicit LockFreePointerQueue(size_t initial_capacity = 1024);
  ~LockFreePointerQueue();

  // Prevent copying
  LockFreePointerQueue(const LockFreePointerQueue&) = delete;
  auto operator=(const LockFreePointerQueue&) -> LockFreePointerQueue& = delete;

  // Allow moving
  LockFreePointerQueue(LockFreePointerQueue&& other) noexcept;
  auto operator=(LockFreePointerQueue&& other) noexcept
      -> LockFreePointerQueue&;

  auto enqueue(T* item) -> bool;
  auto dequeue(T*& item) -> bool;
  auto try_enqueue(T* item) -> bool;
  auto try_dequeue(T*& item) -> bool;

  auto size() const -> size_t;
  auto empty() const -> bool;
  auto capacity() const -> size_t;
  auto clear() -> void;

private:
  static constexpr size_t CACHE_LINE_SIZE = 64;

  struct PointerNode {
    std::atomic<T*> data{nullptr};
    std::atomic<PointerNode*> next{nullptr};
  };

  alignas(CACHE_LINE_SIZE) std::atomic<PointerNode*> head_{nullptr};
  alignas(CACHE_LINE_SIZE) std::atomic<PointerNode*> tail_{nullptr};
  std::atomic<size_t> size_{0};
  std::atomic<size_t> capacity_;

  auto allocate_pointer_node() -> PointerNode*;
  auto deallocate_pointer_node(PointerNode* node) -> void;
};

/**
 * @brief Lock-free bounded queue with fixed capacity
 *
 * High-performance bounded queue using ring buffer with atomic operations.
 */
template <typename T, size_t Capacity>
class LockFreeBoundedQueue {
public:
  static_assert((Capacity & (Capacity - 1)) == 0,
                "Capacity must be power of 2");

  LockFreeBoundedQueue();
  ~LockFreeBoundedQueue() = default;

  // Prevent copying and moving for simplicity
  LockFreeBoundedQueue(const LockFreeBoundedQueue&) = delete;
  LockFreeBoundedQueue(LockFreeBoundedQueue&&) = delete;
  auto operator=(const LockFreeBoundedQueue&) -> LockFreeBoundedQueue& = delete;
  auto operator=(LockFreeBoundedQueue&&) -> LockFreeBoundedQueue& = delete;

  auto enqueue(T item) -> bool;
  auto dequeue(T& item) -> bool;
  auto try_enqueue(T item) -> bool;
  auto try_dequeue(T& item) -> bool;

  auto size() const -> size_t;
  auto empty() const -> bool;
  auto full() const -> bool;
  constexpr auto capacity() const -> size_t { return Capacity; }

private:
  static constexpr size_t MASK = Capacity - 1;
  static constexpr size_t CACHE_LINE_SIZE = 64;

  struct Slot {
    std::atomic<T> data{T{}};
    std::atomic<size_t> sequence{0};
  };

  alignas(CACHE_LINE_SIZE) Slot slots_[Capacity];
  alignas(CACHE_LINE_SIZE) std::atomic<size_t> head_{0};
  alignas(CACHE_LINE_SIZE) std::atomic<size_t> tail_{0};
};

// Template implementation will be provided in separate implementation files

}  // namespace sage_flow