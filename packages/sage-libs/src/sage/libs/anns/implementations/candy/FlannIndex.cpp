//
// Created by Isshin on 2024/3/25.
//
#include "FlannIndex.h"
#include<faiss/utils/distances.h>
#include <Utils/UtilityFunctions.h>

bool CANDY::FlannIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  vecDim = cfg->tryI64("vecDim", 768, true);
  flann_index = cfg->tryI64("flannIndexTag", 2, true);
  allAuto = cfg->tryI64("allAuto", 0, true);
  if (flann_index == FLANN_KMEANS) {
    CANDY::FlannParam best_param;

    INTELLI_INFO("INIT AS FLANN KMEANS TREE!");
    index = new CANDY::KmeansTree();
    index->setConfig(cfg);
  }
  return true;
}

bool CANDY::FlannIndex::loadInitialTensor(torch::Tensor &t) {
  index->addPoints(t);
  return true;
}

bool CANDY::FlannIndex::insertTensor(torch::Tensor &t) {
  index->addPoints(t);
  return true;
}

std::vector<faiss::idx_t> CANDY::FlannIndex::searchIndex(torch::Tensor q, int64_t k) {
  auto querySize = q.size(0);
  std::vector<faiss::idx_t> ru(k * querySize);
  std::vector<float> distance(k * querySize);
  index->knnSearch(q, ru.data(), distance.data(), k);
  return ru;
}

std::vector<torch::Tensor> CANDY::FlannIndex::searchTensor(torch::Tensor &q, int64_t k) {
  auto idx = searchIndex(q, k);
  int64_t size = idx.size() / k;
//    for(int64_t i=0; i<size; i++){
//        auto query_data = q.slice(0,i,i+1).contiguous().data_ptr<float>();
//        printf("obtained result:\n");
//        for (int64_t j = 0; j < k; j++) {
//            int64_t tempIdx = idx[i * k + j];
//            auto data = index->dbTensor.slice(0, tempIdx, tempIdx + 1).contiguous().data_ptr<float>();
//            auto dist = faiss::fvec_L2sqr(query_data, data, vecDim);
//            printf("%ld %f\n", tempIdx, dist);
//        }
//    }
  return getTensorByIndex(idx, k);
}

std::vector<torch::Tensor> CANDY::FlannIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k) {
  int64_t size = idx.size() / k;
  std::vector<torch::Tensor> ru(size);
  for (int64_t i = 0; i < size; i++) {
    ru[i] = torch::zeros({k, vecDim});
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idx[i * k + j];

      if (tempIdx >= 0) {
        ru[i].slice(0, j, j + 1) = index->dbTensor.slice(0, tempIdx, tempIdx + 1);

      };
    }
  }
  return ru;
}
