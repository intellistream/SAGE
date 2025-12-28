/*! \file DistributedIndexWorker.cpp*/
//
// Created by tony on 25/05/23.
//

#include <DistributedPartitionIndex/DistributedIndexWorker.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>

bool CANDY::DIW_RayWrapper::setConfig(std::string cfs) {
  INTELLI::ConfigMapPtr cfg = newConfigMap();
  cfg->fromString(cfs);
  /**
   * @brief 1. find the index algo
   */
  std::string distributedWorker_algoTag = cfg->tryString("distributedWorker_algoTag", "flat", true);
  IndexTable it;
  myIndexAlgo = it.getIndex(distributedWorker_algoTag);
  if (myIndexAlgo == nullptr) {
    return false;
  }
  vecDim = cfg->tryI64("vecDim", 768, true);
  myIndexAlgo->setConfig(cfg);
  return startHPC();
}
bool CANDY::DIW_RayWrapper::insertTensor(std::vector<uint8_t> t) {
  torch::Tensor tx;
  INTELLI::IntelliTensorOP::tensorFromFlatBin(&tx, t);
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->insertTensor(tx);
}
bool CANDY::DIW_RayWrapper::loadInitialTensor(std::vector<uint8_t> t) {
  torch::Tensor tx;
  INTELLI::IntelliTensorOP::tensorFromFlatBin(&tx, t);
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->loadInitialTensor(tx);
}
bool CANDY::DIW_RayWrapper::offlineBuild(std::vector<uint8_t> t) {
  torch::Tensor tx;
  INTELLI::IntelliTensorOP::tensorFromFlatBin(&tx, t);
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->offlineBuild(tx);
}
bool CANDY::DIW_RayWrapper::setFrozenLevel(int64_t frozenLv) {
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->setFrozenLevel(frozenLv);
}
bool CANDY::DIW_RayWrapper::waitPendingOperations() {
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->waitPendingOperations();
}
bool CANDY::DIW_RayWrapper::deleteTensor(std::vector<uint8_t> t, int64_t k) {
  torch::Tensor tx;
  INTELLI::IntelliTensorOP::tensorFromFlatBin(&tx, t);
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->deleteTensor(tx, k);
}
bool CANDY::DIW_RayWrapper::startHPC() {
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->startHPC();
}

bool CANDY::DIW_RayWrapper::endHPC() {
  if (myIndexAlgo == nullptr) {
    return false;
  }
  return myIndexAlgo->endHPC();
}
std::vector<std::vector<uint8_t>> CANDY::DIW_RayWrapper::searchTensor(std::vector<uint8_t> t, int64_t k) {
  torch::Tensor tx;
  INTELLI::IntelliTensorOP::tensorFromFlatBin(&tx, t);
  int64_t tensors = tx.size(0);
  auto ru = std::vector<std::vector<uint8_t>>((size_t) tensors);
  auto ruTemp = myIndexAlgo->searchTensor(tx, k);
  for (size_t i = 0; i < (size_t) tensors; i++) {
    ru[i] = INTELLI::IntelliTensorOP::tensorToFlatBin(&ruTemp[i]);
  }
  return ru;
}
bool CANDY::DIW_RayWrapper::reset() {
  if (myIndexAlgo != nullptr) {
    myIndexAlgo->reset();
    return true;
  }
  return false;
}
RAY_REMOTE(CANDY::DIW_RayWrapper::FactoryCreate,
           &CANDY::DIW_RayWrapper::setConfig,
           &CANDY::DIW_RayWrapper::insertTensor,
           &CANDY::DIW_RayWrapper::deleteTensor,
           &CANDY::DIW_RayWrapper::searchTensor,
           &CANDY::DIW_RayWrapper::reset,
           &CANDY::DIW_RayWrapper::startHPC,
           &CANDY::DIW_RayWrapper::endHPC,
           &CANDY::DIW_RayWrapper::setFrozenLevel,
           &CANDY::DIW_RayWrapper::offlineBuild,
           &CANDY::DIW_RayWrapper::loadInitialTensor,
           &CANDY::DIW_RayWrapper::waitPendingOperations
);

bool CANDY::DistributedIndexWorker::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  cfgString = cfg->toString();
  return true;
}
bool CANDY::DistributedIndexWorker::insertTensor(torch::Tensor &t) {
  auto tx = INTELLI::IntelliTensorOP::tensorToFlatBin(&t);
  auto objRef = workerHandle.Task(&DIW_RayWrapper::insertTensor).Remote(tx);
  auto vc = *(ray::Get(objRef));
  return vc;
}
bool CANDY::DistributedIndexWorker::loadInitialTensor(torch::Tensor &t) {
  auto tx = INTELLI::IntelliTensorOP::tensorToFlatBin(&t);
  auto objRef = workerHandle.Task(&DIW_RayWrapper::loadInitialTensor).Remote(tx);
  auto vc = *(ray::Get(objRef));
  return vc;
}

bool CANDY::DistributedIndexWorker::deleteTensor(torch::Tensor &t, int64_t k) {
  auto tx = INTELLI::IntelliTensorOP::tensorToFlatBin(&t);
  auto objRef = workerHandle.Task(&DIW_RayWrapper::deleteTensor).Remote(tx, k);
  auto vc = *(ray::Get(objRef));
  return vc;
}

bool CANDY::DistributedIndexWorker::waitPendingOperations() {
  auto objRef = workerHandle.Task(&DIW_RayWrapper::waitPendingOperations).Remote();
  auto vc = *(ray::Get(objRef));
  return vc;
}
std::vector<torch::Tensor> CANDY::DistributedIndexWorker::searchTensor(torch::Tensor &q, int64_t k) {
  auto qx = INTELLI::IntelliTensorOP::tensorToFlatBin(&q);
  auto objRef = workerHandle.Task(&DIW_RayWrapper::searchTensor).Remote(qx, k);
  auto ruTemp = *(ray::Get(objRef));
  int64_t tensors = q.size(0);
  auto ru = std::vector<torch::Tensor>((size_t) tensors);
  for (size_t i = 0; i < (size_t) tensors; i++) {
    torch::Tensor tx;
    INTELLI::IntelliTensorOP::tensorFromFlatBin(&tx, ruTemp[i]);
    ru[i] = tx;
  }
  return ru;
}
void CANDY::DistributedIndexWorker::searchTensorUnblock(torch::Tensor &q, int64_t k) {
  auto qx = INTELLI::IntelliTensorOP::tensorToFlatBin(&q);
  lock();
  pendingTensors = q.size(0);
  objRefUnblockedQuery = workerHandle.Task(&DIW_RayWrapper::searchTensor).Remote(qx, k);

  return;
}
std::vector<torch::Tensor> CANDY::DistributedIndexWorker::getUnblockQueryResult() {
  auto ruTemp = *(ray::Get(objRefUnblockedQuery));
  int64_t tensors = pendingTensors;
  unlock();
  auto ru = std::vector<torch::Tensor>((size_t) tensors);
  for (size_t i = 0; i < (size_t) tensors; i++) {
    torch::Tensor tx;
    INTELLI::IntelliTensorOP::tensorFromFlatBin(&tx, ruTemp[i]);
    ru[i] = tx;
  }
  return ru;
}

bool CANDY::DistributedIndexWorker::startHPC() {
  // startThread();
  workerHandle = ray::Actor(DIW_RayWrapper::FactoryCreate).Remote();
  auto objRef = workerHandle.Task(&DIW_RayWrapper::setConfig).Remote(cfgString);
  auto vc = *(ray::Get(objRef));
  return vc;
}
void CANDY::DistributedIndexWorker::reset() {
  auto objRef = workerHandle.Task(&DIW_RayWrapper::reset).Remote();
  auto ruTemp = *(ray::Get(objRef));
  if (ruTemp == false) {
    INTELLI_ERROR("error, failed to distributed reset");
  }
}
bool CANDY::DistributedIndexWorker::endHPC() {
  workerHandle = ray::Actor(DIW_RayWrapper::FactoryCreate).Remote();
  auto objRef = workerHandle.Task(&DIW_RayWrapper::endHPC).Remote();
  auto vc = *(ray::Get(objRef));
  return vc;
}
bool CANDY::DistributedIndexWorker::offlineBuild(torch::Tensor &t) {
  auto tx = INTELLI::IntelliTensorOP::tensorToFlatBin(&t);
  auto objRef = workerHandle.Task(&DIW_RayWrapper::offlineBuild).Remote(tx);
  auto vc = *(ray::Get(objRef));
  return vc;
}
bool CANDY::DistributedIndexWorker::setFrozenLevel(int64_t frozenLv) {
  auto objRef = workerHandle.Task(&DIW_RayWrapper::setFrozenLevel).Remote(frozenLv);
  auto vc = *(ray::Get(objRef));
  return vc;
}
void CANDY::DistributedIndexWorker::loadInitialTensorUnblocked(torch::Tensor &t) {
  auto tx = INTELLI::IntelliTensorOP::tensorToFlatBin(&t);
  lock();
  pendingTensors = t.size(0);
  objRefUnblockedBool = workerHandle.Task(&DIW_RayWrapper::loadInitialTensor).Remote(tx);
  return;
}

void CANDY::DistributedIndexWorker::offlineBuildUnblocked(torch::Tensor &t) {
  auto tx = INTELLI::IntelliTensorOP::tensorToFlatBin(&t);
  lock();
  pendingTensors = t.size(0);
  objRefUnblockedBool = workerHandle.Task(&DIW_RayWrapper::offlineBuild).Remote(tx);
  return;
}

bool CANDY::DistributedIndexWorker::waitPendingBool() {
  auto ruTemp = *(ray::Get(objRefUnblockedBool));
  unlock();
  return ruTemp;
}
