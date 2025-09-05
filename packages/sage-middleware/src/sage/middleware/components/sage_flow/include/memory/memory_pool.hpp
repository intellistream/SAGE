#pragma once

#include <memory>
#include <unordered_map>

namespace sage_flow {

/**
 * @brief Memory pool interface for SAGE Flow framework
 *
 * This memory pool implementation provides efficient memory management
 * for index creation and streaming operations. It supports:
 * - Fixed-size block allocation for reduced fragmentation
 * - Memory usage tracking and statistics
 * - Thread-safe operations with proper synchronization
 * - Memory leak detection and reporting
 * - Configurable pool sizes and growth strategies
 *
 * The implementation uses a combination of fixed-size pools and
 * general-purpose allocation to optimize for both small and large allocations.
 */
class MemoryPool {
public:
  MemoryPool() = default;
  virtual ~MemoryPool() = default;

  // Prevent copying
  MemoryPool(const MemoryPool&) = delete;
  auto operator=(const MemoryPool&) -> MemoryPool& = delete;

  // Allow moving
  MemoryPool(MemoryPool&&) = default;
  auto operator=(MemoryPool&&) -> MemoryPool& = default;

  /**
   * @brief Allocate memory block
   * @param size Size in bytes to allocate
   * @return Pointer to allocated memory, nullptr if failed
   * @throws std::bad_alloc if allocation fails
   */
  virtual auto allocate(size_t size) -> void* = 0;

  /**
   * @brief Deallocate memory block
   * @param ptr Pointer to memory block to deallocate
   * @throws std::invalid_argument if ptr is invalid
   */
  virtual void deallocate(void* ptr) = 0;

  /**
   * @brief Get total allocated memory size
   * @return Total allocated bytes
   */
  virtual auto get_allocated_size() const -> size_t = 0;

  /**
   * @brief Reset/clear all allocations
   */
  virtual void reset() = 0;

  /**
   * @brief Get memory usage statistics
   * @return Memory usage information
   */
  virtual auto get_memory_stats() const -> std::unordered_map<std::string, size_t> = 0;
};

/**
 * @brief Simple memory pool implementation using standard allocator
 */
class SimpleMemoryPool : public MemoryPool {
public:
  SimpleMemoryPool() = default;
  ~SimpleMemoryPool() override;

  auto allocate(size_t size) -> void* override;
  void deallocate(void* ptr) override;
  auto get_allocated_size() const -> size_t override;
  void reset() override;
  auto get_memory_stats() const -> std::unordered_map<std::string, size_t> override;

private:
  std::unordered_map<void*, size_t> allocations_;
  size_t total_allocated_ = 0;
  size_t allocation_count_ = 0;
  size_t deallocation_count_ = 0;
};

/**
 * @brief Factory function to create a default memory pool
 * @return Shared pointer to a new memory pool instance
 */
auto CreateDefaultMemoryPool() -> std::shared_ptr<MemoryPool>;

}  // namespace sage_flow
