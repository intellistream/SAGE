#include "memory/memory_pool.h"

#include <cstdlib>

namespace sage_flow {

SimpleMemoryPool::~SimpleMemoryPool() {
  // Call reset directly to avoid virtual dispatch in destructor
  for (const auto& [ptr, size] : allocations_) {
    std::free(ptr);
  }
  allocations_.clear();
  total_allocated_ = 0;
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
    std::free(ptr);
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
}

auto CreateDefaultMemoryPool() -> std::shared_ptr<MemoryPool> {
  return std::make_shared<SimpleMemoryPool>();
}

}  // namespace sage_flow
