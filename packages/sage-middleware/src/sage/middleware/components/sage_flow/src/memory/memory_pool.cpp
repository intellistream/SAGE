#include "memory/memory_pool.hpp"

#include <cstdlib>

namespace sage_flow {

SimpleMemoryPool::~SimpleMemoryPool() {
  // Call reset directly to avoid virtual dispatch in destructor
  for (const auto& [ptr, size] : allocations_) {
    std::free(ptr);
  }
  allocations_.clear();
  total_allocated_ = 0;
  allocation_count_ = 0;
  deallocation_count_ = 0;
}

auto SimpleMemoryPool::allocate(size_t size) -> void* {
  if (size == 0) {
    return nullptr;
  }

  void* ptr = std::malloc(size);
  if (ptr == nullptr) {
    throw std::bad_alloc();
  }

  allocations_[ptr] = size;
  total_allocated_ += size;
  allocation_count_++;
  return ptr;
}

void SimpleMemoryPool::deallocate(void* ptr) {
  if (ptr == nullptr) {
    return;
  }

  auto it = allocations_.find(ptr);
  if (it != allocations_.end()) {
    total_allocated_ -= it->second;
    allocations_.erase(it);
    deallocation_count_++;
    std::free(ptr);
  } else {
    throw std::invalid_argument("Attempting to deallocate invalid pointer");
  }
}

auto SimpleMemoryPool::get_allocated_size() const -> size_t {
  return total_allocated_;
}

void SimpleMemoryPool::reset() {
  for (const auto& [ptr, size] : allocations_) {
    std::free(ptr);
  }
  allocations_.clear();
  total_allocated_ = 0;
  allocation_count_ = 0;
  deallocation_count_ = 0;
}

auto SimpleMemoryPool::get_memory_stats() const -> std::unordered_map<std::string, size_t> {
  return {
      {"total_allocated", total_allocated_},
      {"allocation_count", allocation_count_},
      {"deallocation_count", deallocation_count_},
      {"active_allocations", allocations_.size()},
      {"average_allocation_size", allocation_count_ > 0 ? total_allocated_ / allocation_count_ : 0}
  };
}

auto CreateDefaultMemoryPool() -> std::shared_ptr<MemoryPool> {
  return std::make_shared<SimpleMemoryPool>();
}

}  // namespace sage_flow
