/*! \file DistributedPartitionIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include "DistributedPartitionIndex.h"
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
void CANDY::DistributedPartitionIndex::reset() {

}

bool CANDY::DistributedPartitionIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  distributedWorkers = cfg->tryI64("distributedWorkers", 1, true);
  workers = std::vector<DistributedIndexWorkerPtr>((size_t) distributedWorkers);
  fineGrainedDistributedInsert = cfg->tryI64("fineGrainedDistributedInsert", 0, true);
  //reduceQueue=std::make_shared<INTELLI::SPSCQueue<CANDY::TensorListIdxPair>>((size_t)(distributedWorkers*10));
  vecDim = cfg->tryI64("vecDim", 768, true);
  sharedBuild = cfg->tryI64("sharedBuild", 1, true);
  for (size_t i = 0; i < (size_t) distributedWorkers; i++) {
    workers[i] = newDistributedIndexWorker();
    workers[i]->setConfig(cfg);
  }
  insertIdx = 0;

  return true;
}
void CANDY::DistributedPartitionIndex::insertTensorInline(torch::Tensor t) {
  workers[(size_t) insertIdx]->insertTensor(t);
  insertIdx++;
  if (insertIdx >= distributedWorkers) {
    insertIdx = 0;
  }
}
bool CANDY::DistributedPartitionIndex::insertTensor(torch::Tensor &t) {

  if (!fineGrainedDistributedInsert) {
    insertTensorInline(t);
  } else {
    int64_t rows = t.size(0);
    for (int64_t i = 0; i < rows; i++) {
      auto rowI = t.slice(0, i, i + 1);
      insertTensorInline(rowI);
    }
  }
  return true;
}

bool CANDY::DistributedPartitionIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  /**
    * @brief 1. map
    */
  size_t tensors = (size_t) t.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  std::vector<torch::Tensor> ru(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * distributedWorkers, vecDim});
    ru[i] = torch::zeros({k, vecDim});
  }
  int64_t collectedRu = 0;
  while (collectedRu < distributedWorkers) {
    auto tlpt = workers[collectedRu]->searchTensor(t, k);
    for (size_t i = 0; i < tensors; i++) {
      ruTemp[i].slice(0, k * collectedRu, k * collectedRu + k) = tlpt[i];
    }
    INTELLI_INFO("get result from " + std::to_string(collectedRu) + " th worker");
    collectedRu++;
  }
  INTELLI_INFO("collection is done");

  /**
  * @brief 2. reduce
  */
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto queryTensor = t.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * distributedWorkers, dbData); // add vectors to the index
    int64_t querySize = 1;
    std::vector<faiss::idx_t> idxRu(k * querySize);
    std::vector<float> distance(k * querySize);
    indexFlat.search(querySize, queryData, k, distance.data(), idxRu.data());
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idxRu[j];
      int64_t workerNo = tempIdx / k;
      auto tensorToDelete = dbTensor.slice(0, tempIdx, tempIdx + 1);
      workers[workerNo]->deleteTensor(tensorToDelete, 1);
      INTELLI_INFO("tell worker" + std::to_string(workerNo) + " to delete tensor");
    }
  }
  return true;
}

bool CANDY::DistributedPartitionIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  //assert(t.size(1) == w.size(1));
  /**
   * @brief only allow to delete and insert, no straightforward revision
   */
  deleteTensor(t, 1);
  insertTensor(w);
  return true;
}

std::vector<torch::Tensor> CANDY::DistributedPartitionIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx,
                                                                              int64_t k) {
  assert(k > 0);
  assert(idx.size());
  std::vector<torch::Tensor> ru(1);
  ru[0] = torch::rand({1, 1});
  return ru;
}
torch::Tensor CANDY::DistributedPartitionIndex::rawData() {
  return torch::rand({1, 1});
}

void CANDY::DistributedPartitionIndex::partitionBuildInLine(torch::Tensor &t) {
  int64_t rows = t.size(0);
  std::vector<int64_t> startPos((size_t) distributedWorkers);
  std::vector<int64_t> endPos((size_t) distributedWorkers);
  startPos = std::vector<int64_t>((size_t) distributedWorkers);

  int64_t step = rows / distributedWorkers;
  startPos[0] = 0;
  endPos[distributedWorkers - 1] = rows;
  int64_t stepAcc = step;
  for (int64_t i = 1; i < distributedWorkers; i++) {
    startPos[i] = stepAcc;
    stepAcc += step;
  }
  stepAcc = step;
  for (int64_t i = 0; i < distributedWorkers - 1; i++) {
    endPos[i] = stepAcc;
    stepAcc += step;
  }
  for (int64_t i = 0; i < distributedWorkers; i++) {
    auto subTensor = t.slice(0, startPos[i], endPos[i]);
    workers[i]->offlineBuildUnblocked(subTensor);
  }
  for (int64_t i = 0; i < distributedWorkers; i++) {
    workers[i]->waitPendingBool();
  }
}
void CANDY::DistributedPartitionIndex::partitionLoadInLine(torch::Tensor &t) {
  int64_t rows = t.size(0);
  std::vector<int64_t> startPos((size_t) distributedWorkers);
  std::vector<int64_t> endPos((size_t) distributedWorkers);
  startPos = std::vector<int64_t>((size_t) distributedWorkers);

  int64_t step = rows / distributedWorkers;
  startPos[0] = 0;
  endPos[distributedWorkers - 1] = rows;
  int64_t stepAcc = step;
  for (int64_t i = 1; i < distributedWorkers; i++) {
    startPos[i] = stepAcc;
    stepAcc += step;
  }
  stepAcc = step;
  for (int64_t i = 0; i < distributedWorkers - 1; i++) {
    endPos[i] = stepAcc;
    stepAcc += step;
  }
  for (int64_t i = 0; i < distributedWorkers; i++) {
    auto subTensor = t.slice(0, startPos[i], endPos[i]);
    workers[i]->loadInitialTensorUnblocked(subTensor);
  }
  for (int64_t i = 0; i < distributedWorkers; i++) {
    workers[i]->waitPendingBool();
  }
}
std::vector<torch::Tensor> CANDY::DistributedPartitionIndex::searchTensor(torch::Tensor &q, int64_t k) {

  /**
   * @brief 1. map
   */
  size_t tensors = (size_t) q.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  std::vector<torch::Tensor> ru(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * distributedWorkers, vecDim});
    ru[i] = torch::zeros({k, vecDim});
  }

  for (int64_t i = 0; i < distributedWorkers; i++) {
    workers[i]->searchTensorUnblock(q, k);
  }
  int64_t collectedRu = 0;
  while (collectedRu < distributedWorkers) {
    // auto tlpt = workers[collectedRu]->searchTensor(q, k);
    auto tlpt = workers[collectedRu]->getUnblockQueryResult();
    for (size_t i = 0; i < tensors; i++) {
      ruTemp[i].slice(0, k * collectedRu, k * collectedRu + k) = tlpt[i];
    }
    INTELLI_INFO("get result from " + std::to_string(collectedRu) + " th worker");
    collectedRu++;
  }
  INTELLI_INFO("collection is done");
  /**
  * @brief 2. reduce
  */
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto queryTensor = q.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * distributedWorkers, dbData); // add vectors to the index
    int64_t querySize = 1;
    std::vector<faiss::idx_t> idxRu(k * querySize);
    std::vector<float> distance(k * querySize);
    indexFlat.search(querySize, queryData, k, distance.data(), idxRu.data());
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idxRu[j];
      if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1); }
    }
  }
  return ru;
}
bool CANDY::DistributedPartitionIndex::startHPC() {
  ray::Init();
  for (size_t i = 0; i < (size_t) distributedWorkers; i++) {
    workers[i]->startHPC();
  }
  return true;
}

bool CANDY::DistributedPartitionIndex::endHPC() {
  for (size_t i = 0; i < (size_t) distributedWorkers; i++) {
    workers[i]->endHPC();
  }
  ray::Shutdown();
  return true;
}

bool CANDY::DistributedPartitionIndex::offlineBuild(torch::Tensor &t) {
  if (sharedBuild) {
    for (size_t i = 0; i < (size_t) distributedWorkers; i++) {
      workers[i]->offlineBuildUnblocked(t);
    }
    for (size_t i = 0; i < (size_t) distributedWorkers; i++) {
      workers[i]->waitPendingBool();
    }

  } else {
    partitionBuildInLine(t);
  }
  return true;
}

bool CANDY::DistributedPartitionIndex::loadInitialTensor(torch::Tensor &t) {
  partitionLoadInLine(t);
  return true;
}
bool CANDY::DistributedPartitionIndex::setFrozenLevel(int64_t frozenLv) {
  for (size_t i = 0; i < (size_t) distributedWorkers; i++) {
    workers[i]->setFrozenLevel(frozenLv);
  }
  return true;
}
bool CANDY::DistributedPartitionIndex::waitPendingOperations() {
  for (size_t i = 0; i < (size_t) distributedWorkers; i++) {
    workers[i]->waitPendingOperations();
  }
  return true;
}
