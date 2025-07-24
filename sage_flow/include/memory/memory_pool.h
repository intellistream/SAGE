#pragma once

#include <memory>
#include <unordered_map>

namespace sage_flow {

/**
 * @brief Memory pool interface for SAGE Flow framework
 * 
 * This is a simplified memory pool implementation to support
 * index creation and basic memory management needs.
 * 
 * TODO(developer): Implement full memory pool functionality
 Issue URL: https://github.com/intellistream/SAGE/issues/350
 * when more sophisticated memory management is required.
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
   */
  virtual auto allocate(size_t size) -> void* = 0;

  /**
   * @brief Deallocate memory block
   * @param ptr Pointer to memory block to deallocate
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

 private:
  std::unordered_map<void*, size_t> allocations_;
  size_t total_allocated_ = 0;
};

/**
 * @brief Factory function to create a default memory pool
 * @return Shared pointer to a new memory pool instance
 */
auto CreateDefaultMemoryPool() -> std::shared_ptr<MemoryPool>;

}  // namespace sage_flow
