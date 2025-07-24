#include "index/index_operators.h"

#include "index/brute_force_index.h"
#include "index/hnsw_index.h"
#include "index/knn_operator.h"
#include "index/itopk_operator.h"

namespace sage_flow {

auto CreateIndex(IndexType type, 
                std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<Index> {
  switch (type) {
    case IndexType::kBruteForce:
      return std::make_unique<BruteForceIndex>(std::move(memory_pool));
    case IndexType::kHnsw:
      return std::make_unique<HnswIndex>(std::move(memory_pool));
    case IndexType::kNone:
    case IndexType::kIvf:
    case IndexType::kKnn:
    case IndexType::kVectraFlow:
    default:
      // Return BruteForce as default fallback
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
