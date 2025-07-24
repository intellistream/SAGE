#include "index/index_operators.h"
#include "index/brute_force_index.h"
#include "index/hnsw.h"
#include "index/ivf.h"

#include <memory>

namespace sage_flow {

// Factory function implementations
auto CreateIndex(IndexType type, 
                std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<Index> {
  switch (type) {
    case IndexType::kBruteForce:
      return std::make_unique<BruteForceIndex>(std::move(memory_pool));
    case IndexType::kHnsw:
      return std::make_unique<HNSW>(std::move(memory_pool));
    case IndexType::kIvf:
      return std::make_unique<IVF>(std::move(memory_pool));
    case IndexType::kAdaIvf:
    case IndexType::kVectraFlow:
    case IndexType::kVamana:
    case IndexType::kFreshVamana:
    case IndexType::kDynaGraph:
    case IndexType::kSpFresh:
    case IndexType::kKnn:
    default:
      // TODO(developer): Implement other indexes
      // For now, use brute force as fallback for all unimplemented types
      return std::make_unique<BruteForceIndex>(std::move(memory_pool));
  }
}

}  // namespace sage_flow
