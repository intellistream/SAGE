/*! \file FlatIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <FlatIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
bool CANDY::FlatIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  vecDim = cfg->tryI64("vecDim", 768, true);
  initialVolume = cfg->tryI64("initialVolume", 1000, true);
  expandStep = cfg->tryI64("expandStep", 100, true);
  dbTensor = torch::zeros({initialVolume, vecDim});
  lastNNZ = -1;
  return true;
}
void CANDY::FlatIndex::reset() {
  lastNNZ = -1;
}
bool CANDY::FlatIndex::insertTensor(torch::Tensor &t) {
  return INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &t, &lastNNZ, expandStep);
}

bool CANDY::FlatIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  std::vector<faiss::idx_t> idxToDelete = searchIndex(t, k);
  std::vector<int64_t> &int64Vector = reinterpret_cast<std::vector<int64_t> &>(idxToDelete);
  return INTELLI::IntelliTensorOP::deleteRowsBufferMode(&dbTensor, int64Vector, &lastNNZ);
}

bool CANDY::FlatIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  if (t.size(0) > w.size(0) || t.size(1) != w.size(1)) {
    return false;
  }
  int64_t rows = t.size(0);
  faiss::IndexFlat indexFlat(vecDim); // call constructor
  float *dbData = dbTensor.contiguous().data_ptr<float>();
  indexFlat.add(lastNNZ + 1, dbData); // add vectors to the index
  for (int64_t i = 0; i < rows; i++) {
    float distance;
    faiss::idx_t idx;
    auto rowI = t.slice(0, i, i + 1).contiguous();
    float *queryData = rowI.data_ptr<float>();
    indexFlat.search(1, queryData, 1, &distance, &idx);
    if (0 <= idx && idx <= lastNNZ) {
      auto rowW = w.slice(0, i, i + 1);
      INTELLI::IntelliTensorOP::editRows(&dbTensor, &rowW, (int64_t) idx);
    }
  }
  return true;
}
std::vector<faiss::idx_t> CANDY::FlatIndex::searchIndex(torch::Tensor q, int64_t k) {
  faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
  float *dbData = dbTensor.contiguous().data_ptr<float>();
  float *queryData = q.contiguous().data_ptr<float>();
  indexFlat.add(lastNNZ + 1, dbData); // add vectors to the index
  int64_t querySize = q.size(0);
  std::vector<faiss::idx_t> ru(k * querySize);
  std::vector<float> distance(k * querySize);
  indexFlat.search(querySize, queryData, k, distance.data(), ru.data());
  return ru;
}

std::vector<torch::Tensor> CANDY::FlatIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k) {
  int64_t tensors = idx.size() / k;
  std::vector<torch::Tensor> ru(tensors);

  for (int64_t i = 0; i < tensors; i++) {
    ru[i] = torch::zeros({k, vecDim});
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idx[i * k + j];
      if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1); }
    }
  }
  return ru;
}
torch::Tensor CANDY::FlatIndex::rawData() {
  return dbTensor.slice(0, 0, lastNNZ + 1).contiguous();
}

std::vector<torch::Tensor> CANDY::FlatIndex::searchTensor(torch::Tensor &q, int64_t k) {
  auto idx = searchIndex(q, k);
  return getTensorByIndex(idx, k);
}
