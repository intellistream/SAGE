/*! \file CongestionDropIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <CongestionDropIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
#include <thread>
void CANDY::CongestionDropIndex::reset() {

}

bool CANDY::CongestionDropIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  parallelWorkers = cfg->tryI64("parallelWorkers", 1, true);
  if (parallelWorkers <= 0) {
    parallelWorkers = std::thread::hardware_concurrency();
  }
  workers = std::vector<CongestionDropIndexWorkerPtr>((size_t) parallelWorkers);
  reduceQueue = std::vector<TensorListIdxQueuePtr>(parallelWorkers);
  fineGrainedParallelInsert = cfg->tryI64("fineGrainedParallelInsert", 0, true);
  //reduceQueue=std::make_shared<INTELLI::SPSCQueue<CANDY::TensorListIdxPair>>((size_t)(parallelWorkers*10));
  vecDim = cfg->tryI64("vecDim", 768, true);
  sharedBuild = cfg->tryI64("sharedBuild", 1, true);
  singleWorkerOpt = cfg->tryI64("singleWorkerOpt", 1, true);
  reduceStrQueue = std::vector<TensorStrVecQueuePtr>(parallelWorkers);
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i] = newCongestionDropIndexWorker();
    workers[i]->setConfig(cfg);
    workers[i]->setId(i);
    reduceQueue[i] = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorListIdxPair>>((size_t) (10));
    reduceStrQueue[i] = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorStrVecPair>>((size_t) (10));
    workers[i]->setReduceQueue(reduceQueue[i]);
    workers[i]->setReduceStrQueue(reduceStrQueue[i]);
  }
  insertIdx = 0;

  return true;
}
void CANDY::CongestionDropIndex::insertTensorInline(torch::Tensor &t) {
  workers[(size_t) insertIdx]->insertTensor(t);
  insertIdx++;
  if (insertIdx >= parallelWorkers) {
    insertIdx = 0;
  }
}
void CANDY::CongestionDropIndex::partitionLoadInLine(torch::Tensor &t) {
  int64_t rows = t.size(0);
  std::vector<int64_t> startPos((size_t) parallelWorkers);
  std::vector<int64_t> endPos((size_t) parallelWorkers);
  startPos = std::vector<int64_t>((size_t) parallelWorkers);

  int64_t step = rows / parallelWorkers;
  startPos[0] = 0;
  endPos[parallelWorkers - 1] = rows;
  int64_t stepAcc = step;
  for (int64_t i = 1; i < parallelWorkers; i++) {
    startPos[i] = stepAcc;
    stepAcc += step;
  }
  stepAcc = step;
  for (int64_t i = 0; i < parallelWorkers - 1; i++) {
    endPos[i] = stepAcc;
    stepAcc += step;
  }
  for (int64_t i = 0; i < parallelWorkers; i++) {
    auto subTensor = t.slice(0, startPos[i], endPos[i]);
    workers[i]->loadInitialTensor(subTensor);
  }
}
void CANDY::CongestionDropIndex::partitionBuildInLine(torch::Tensor &t) {
  int64_t rows = t.size(0);
  std::vector<int64_t> startPos((size_t) parallelWorkers);
  std::vector<int64_t> endPos((size_t) parallelWorkers);
  startPos = std::vector<int64_t>((size_t) parallelWorkers);

  int64_t step = rows / parallelWorkers;
  startPos[0] = 0;
  endPos[parallelWorkers - 1] = rows;
  int64_t stepAcc = step;
  for (int64_t i = 1; i < parallelWorkers; i++) {
    startPos[i] = stepAcc;
    stepAcc += step;
  }
  stepAcc = step;
  for (int64_t i = 0; i < parallelWorkers - 1; i++) {
    endPos[i] = stepAcc;
    stepAcc += step;
  }
  for (int64_t i = 0; i < parallelWorkers; i++) {
    auto subTensor = t.slice(0, startPos[i], endPos[i]);
    workers[i]->offlineBuild(subTensor);
  }
}

bool CANDY::CongestionDropIndex::insertTensor(torch::Tensor &t) {

  if (!fineGrainedParallelInsert) {
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

bool CANDY::CongestionDropIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  /**
  * @brief 1. broadcast the query
  */
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->pushSearch(t, k);
  }
  /**
   * @brief 2. prepare to collect
   */
  size_t tensors = (size_t) t.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  //std::vector<torch::Tensor> ru(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * parallelWorkers, vecDim});
  }
  int64_t collectedRu = 0;
  while (collectedRu < parallelWorkers) {
    while (reduceQueue[collectedRu]->empty()) {

    }

    auto tlp = *reduceQueue[collectedRu]->front();
    reduceQueue[collectedRu]->pop();
    for (size_t i = 0; i < tensors; i++) {
      ruTemp[i].slice(0, k * tlp.idx, k * tlp.idx + k) = tlp.t[i];
    }
    INTELLI_INFO("get result from " + std::to_string(tlp.idx) + " th worker");
    collectedRu++;
  }
  INTELLI_INFO("collection is done");
  /**
  * @brief 3. reduce
  */
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto queryTensor = t.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * parallelWorkers, dbData); // add vectors to the index
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
      // if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1); }
    }
  }
  return true;
}

bool CANDY::CongestionDropIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  //assert(t.size(1) == w.size(1));
  /**
   * @brief only allow to delete and insert, no straightforward revision
   */
  deleteTensor(t, 1);
  insertTensor(w);
  return true;
}

bool CANDY::CongestionDropIndex::loadInitialTensor(torch::Tensor &t) {
  if (workers.size() == 1 && singleWorkerOpt) {
    INTELLI_INFO("Initial tensor load single worker mode");
    //workers[0]->waitPendingOperations();
    workers[0]->loadInitialTensor(t);
    usleep(100000);
    workers[0]->waitPendingOperations();
    return true;
  }
  partitionLoadInLine(t);
  usleep(1000);
  INTELLI_INFO("Initial tensor load start");
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->waitPendingOperations();
  }
  INTELLI_INFO("Initial tensor load done");
  return true;
}
std::vector<torch::Tensor> CANDY::CongestionDropIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k) {
  assert(k > 0);
  assert(idx.size());
  std::vector<torch::Tensor> ru(1);
  ru[0] = torch::rand({1, 1});
  return ru;
}
torch::Tensor CANDY::CongestionDropIndex::rawData() {
  return torch::rand({1, 1});
}

std::vector<torch::Tensor> CANDY::CongestionDropIndex::searchTensor(torch::Tensor &q, int64_t k) {
  if (workers.size() == 1 && singleWorkerOpt) {
    workers[0]->waitPendingOperations();
    return workers[0]->searchTensor(q, k);
  }
  /**
   * @brief 1. broadcast the query
   */
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->pushSearch(q, k);
  }
  /**
   * @brief 2. prepare to collect
   */
  size_t tensors = (size_t) q.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  std::vector<torch::Tensor> ru(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * parallelWorkers, vecDim});
    ru[i] = torch::zeros({k, vecDim});
  }
  int64_t collectedRu = 0;
  while (collectedRu < parallelWorkers) {
    while (reduceQueue[collectedRu]->empty()) {

    }
    auto tlp = *reduceQueue[collectedRu]->front();
    reduceQueue[collectedRu]->pop();
    for (size_t i = 0; i < tensors; i++) {
      ruTemp[i].slice(0, k * tlp.idx, k * tlp.idx + k) = tlp.t[i];
    }
    INTELLI_INFO("get result from " + std::to_string(tlp.idx) + " th worker");
    collectedRu++;
  }
  INTELLI_INFO("collection is done");
  /**
  * @brief 3. reduce
  */
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto queryTensor = q.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * parallelWorkers, dbData); // add vectors to the index
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
bool CANDY::CongestionDropIndex::startHPC() {
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->startHPC();
  }
  return true;
}

bool CANDY::CongestionDropIndex::endHPC() {
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->endHPC();
  }
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->joinThread();
  }

  return true;
}

bool CANDY::CongestionDropIndex::offlineBuild(torch::Tensor &t) {
  if (sharedBuild) {
    for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
      workers[i]->offlineBuild(t);
    }
  } else {
    partitionBuildInLine(t);
  }
  return true;
}
bool CANDY::CongestionDropIndex::setFrozenLevel(int64_t frozenLv) {
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->setFrozenLevel(frozenLv);
  }
  return true;
}
bool CANDY::CongestionDropIndex::waitPendingOperations() {
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->waitPendingOperations();
  }
  return true;
}

std::tuple<std::vector<torch::Tensor>,
           std::vector<std::vector<std::string>>> CANDY::CongestionDropIndex::searchTensorAndStringObject(torch::Tensor &q,
                                                                                                          int64_t k) {
  if (workers.size() == 1 && singleWorkerOpt) {
    workers[0]->waitPendingOperations();
    return workers[0]->searchTensorAndStringObject(q, k);
  }
  /**
   * @brief 1. broadcast the query
   */
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->pushSearchStr(q, k);
  }
  //INTELLI_INFO("push is done");
  /**
   * @brief 2. prepare to collect
   */
  size_t tensors = (size_t) q.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  std::vector<torch::Tensor> ru(tensors);
  std::vector<std::vector<std::string>> ruStringTemp(tensors);
  std::vector<std::vector<std::string>> ruString(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * parallelWorkers, vecDim});
    ru[i] = torch::zeros({k, vecDim});
    ruStringTemp[i] = std::vector<std::string>(k * parallelWorkers);
    ruString[i] = std::vector<std::string>(k);
  }
  int64_t collectedRu = 0;
  //INTELLI_INFO("enter collection");
  while (collectedRu < parallelWorkers) {
    while (reduceStrQueue[collectedRu]->empty()) {

    }
    auto tlp = *reduceStrQueue[collectedRu]->front();
    // auto tlp = *reduceQueue[collectedRu]->front();
    reduceStrQueue[collectedRu]->pop();
    for (size_t i = 0; i < tensors; i++) {
      ruTemp[i].slice(0, k * tlp.idx, k * tlp.idx + k) = tlp.t[i];
      std::copy(tlp.strObjs[i].begin(), tlp.strObjs[i].end(), ruStringTemp[i].begin() + k * tlp.idx);
    }
    INTELLI_INFO("get result from " + std::to_string(tlp.idx) + " th worker");
    collectedRu++;
  }
  INTELLI_INFO("collection is done");
  if (workers.size() == 1) {
    std::tuple<std::vector<torch::Tensor>, std::vector<std::vector<std::string>>> ruTuple(ruTemp, ruStringTemp);
    return ruTuple;
  }
  /**
  * @brief 3. reduce
  */
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto dbString = ruStringTemp[i];
    auto queryTensor = q.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * parallelWorkers, dbData); // add vectors to the index
    int64_t querySize = 1;
    std::vector<faiss::idx_t> idxRu(k * querySize);
    std::vector<float> distance(k * querySize);
    indexFlat.search(querySize, queryData, k, distance.data(), idxRu.data());
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idxRu[j];
      if (tempIdx >= 0) {
        ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1);
        ruString[i][j] = dbString[tempIdx];
      }
    }
  }
  std::tuple<std::vector<torch::Tensor>, std::vector<std::vector<std::string>>> ruTuple(ru, ruString);
  return ruTuple;
}
std::vector<std::vector<std::string>> CANDY::CongestionDropIndex::searchStringObject(torch::Tensor &q, int64_t k) {
  if (workers.size() == 1 && singleWorkerOpt) {
    workers[0]->waitPendingOperations();
    return workers[0]->searchStringObject(q, k);
  }
  auto ru = searchTensorAndStringObject(q, k);
  return std::get<1>(ru);
}

void CANDY::CongestionDropIndex::insertStringInline(torch::Tensor &t, std::vector<string> &s) {
  workers[(size_t) insertIdx]->insertStringObject(t, s);
  insertIdx++;
  if (insertIdx >= parallelWorkers) {
    insertIdx = 0;
  }
}
void CANDY::CongestionDropIndex::partitionLoadStringInLine(torch::Tensor &t, std::vector<std::string> &strs) {
  int64_t rows = t.size(0);
  std::vector<int64_t> startPos((size_t) parallelWorkers);
  std::vector<int64_t> endPos((size_t) parallelWorkers);
  startPos = std::vector<int64_t>((size_t) parallelWorkers);

  int64_t step = rows / parallelWorkers;
  startPos[0] = 0;
  endPos[parallelWorkers - 1] = rows;
  int64_t stepAcc = step;
  for (int64_t i = 1; i < parallelWorkers; i++) {
    startPos[i] = stepAcc;
    stepAcc += step;
  }
  stepAcc = step;
  for (int64_t i = 0; i < parallelWorkers - 1; i++) {
    endPos[i] = stepAcc;
    stepAcc += step;
  }
  for (int64_t i = 0; i < parallelWorkers; i++) {
    auto subTensor = t.slice(0, startPos[i], endPos[i]);
    auto subStr = std::vector<std::string>(strs.begin() + startPos[i], strs.begin() + endPos[i]);
    workers[i]->loadInitialStringObject(subTensor, subStr);
  }

}

bool CANDY::CongestionDropIndex::insertStringObject(torch::Tensor &t, std::vector<std::string> &strs) {
  if (!fineGrainedParallelInsert) {
    insertStringInline(t, strs);
  } else {
    int64_t rows = t.size(0);
    for (int64_t i = 0; i < rows; i++) {
      auto rowI = t.slice(0, i, i + 1);
      auto rowIs = std::vector<std::string>(strs.begin() + i, strs.begin() + i + 1);
      insertStringInline(rowI, rowIs);
    }
  }
  return true;

}
bool CANDY::CongestionDropIndex::deleteStringObject(torch::Tensor &t, int64_t k) {
  /**
  * @brief 1. broadcast the query
  */
  for (size_t i = 0; i < (size_t) parallelWorkers; i++) {
    workers[i]->pushSearch(t, k);
  }
  /**
   * @brief 2. prepare to collect
   */
  size_t tensors = (size_t) t.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  //std::vector<torch::Tensor> ru(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * parallelWorkers, vecDim});
  }
  int64_t collectedRu = 0;
  while (collectedRu < parallelWorkers) {
    while (reduceQueue[collectedRu]->empty()) {

    }

    auto tlp = *reduceQueue[collectedRu]->front();
    reduceQueue[collectedRu]->pop();
    for (size_t i = 0; i < tensors; i++) {
      ruTemp[i].slice(0, k * tlp.idx, k * tlp.idx + k) = tlp.t[i];
    }
    INTELLI_INFO("get result from " + std::to_string(tlp.idx) + " th worker");
    collectedRu++;
  }
  INTELLI_INFO("collection is done");
  /**
  * @brief 3. reduce
  */
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto queryTensor = t.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * parallelWorkers, dbData); // add vectors to the index
    int64_t querySize = 1;
    std::vector<faiss::idx_t> idxRu(k * querySize);
    std::vector<float> distance(k * querySize);
    indexFlat.search(querySize, queryData, k, distance.data(), idxRu.data());
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idxRu[j];
      int64_t workerNo = tempIdx / k;
      auto tensorToDelete = dbTensor.slice(0, tempIdx, tempIdx + 1);
      workers[workerNo]->deleteStringObject(tensorToDelete, 1);
      INTELLI_INFO("tell worker" + std::to_string(workerNo) + " to delete tensor");
      // if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1); }
    }
  }
  return true;
}

bool CANDY::CongestionDropIndex::loadInitialStringObject(torch::Tensor &t, std::vector<std::string> &strs) {
  partitionLoadStringInLine(t, strs);
  return true;
}
