#include "index/index_operators.h"

#include <memory>
#include <utility>

namespace sage_flow {

// Forward declarations for factory functions
class MemoryPool;

// Factory function implementations
auto CreateIndex(IndexType type, 
                std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<Index> {
  switch (type) {
    case IndexType::kBruteForce:
      return std::make_unique<BruteForceIndex>(std::move(memory_pool));
    case IndexType::kHnsw:
      return std::make_unique<HnswIndex>(std::move(memory_pool));
    case IndexType::kIvf:
    case IndexType::kKnn:
    case IndexType::kVectraFlow:
    default:
      // TODO(developer): Implement IVF, VectraFlow indexes
      // For now, use brute force as fallback for all unimplemented types
      return std::make_unique<BruteForceIndex>(std::move(memory_pool));
  }
}

auto CreateKnnOperator(std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<KnnOperator> {
  return std::make_unique<KnnOperator>(std::move(memory_pool));
}

auto CreateTopKOperator(std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<ITopKOperator> {
  return std::make_unique<TopKOperator>(std::move(memory_pool));
}

}  // namespace sage_flow
