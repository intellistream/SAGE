/*! \file CongestionDropIndexWorker.cpp*/
//
// Created by tony on 25/05/23.
//

#include <CongestionDropIndex/CongestionDropIndexWorker.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
bool CANDY::CongestionDropIndexWorker::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  /**
   * @brief 1. find the index algo
   */
  std::string parallelWorker_algoTag = cfg->tryString("congestionDropWorker_algoTag", "flat", true);
  IndexTable it;
  myIndexAlgo = it.getIndex(parallelWorker_algoTag);
  if (myIndexAlgo == nullptr) {
    return false;
  }
  vecDim = cfg->tryI64("vecDim", 768, true);
  congestionDrop = cfg->tryI64("congestionDrop", 1, true);
  INTELLI_INFO("Congestion drop =" + to_string(congestionDrop));
  myIndexAlgo->setConfig(cfg);
  /**
   * @brief 2. set up the queues
   */
  int64_t parallelWorker_queueSize = cfg->tryI64("congestionDropWorker_queueSize", 10, true);
  forceDrop = cfg->tryI64("forceDrop", 1, true);
  if (parallelWorker_queueSize < 0) {
    parallelWorker_queueSize = 10;
  }
  buildQueue = std::make_shared<INTELLI::SPSCQueue<torch::Tensor>>((size_t) parallelWorker_queueSize);
  insertQueue = std::make_shared<INTELLI::SPSCQueue<torch::Tensor>>((size_t) parallelWorker_queueSize);
  initialLoadQueue = std::make_shared<INTELLI::SPSCQueue<torch::Tensor>>((size_t) parallelWorker_queueSize);
  reviseQueue0 = std::make_shared<INTELLI::SPSCQueue<torch::Tensor>>((size_t) parallelWorker_queueSize);
  reviseQueue1 = std::make_shared<INTELLI::SPSCQueue<torch::Tensor>>((size_t) parallelWorker_queueSize);
  deleteQueue = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorIdxPair>>((size_t) parallelWorker_queueSize);
  queryQueue = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorIdxPair>>((size_t) parallelWorker_queueSize);
  queryStrQueue = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorIdxPair>>((size_t) parallelWorker_queueSize);
  cmdQueue = std::make_shared<INTELLI::SPSCQueue<int64_t>>((size_t) parallelWorker_queueSize);
  initialStrQueue = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorStrPair>>((size_t) parallelWorker_queueSize);
  insertStrQueue = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorStrPair>>((size_t) parallelWorker_queueSize);
  deleteStrQueue = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorIdxPair>>((size_t) parallelWorker_queueSize);

  //setId(1);
  return true;
}
bool CANDY::CongestionDropIndexWorker::insertTensor(torch::Tensor &t) {
  /*if(insertQueue->empty()||(!forceDrop)) {
    ingestedVectors+=t.size(0);
    insertQueue->push(t);
  }
  else {
    INTELLI_WARNING("Drop data");
  }*/
  return ParallelIndexWorker::insertTensor(t);
}

std::vector<torch::Tensor> CANDY::CongestionDropIndexWorker::searchTensor(torch::Tensor &q, int64_t k) {
  if (ingestedVectors > k) {
    return ParallelIndexWorker::searchTensor(q, k);
  } else {
    INTELLI_ERROR("Insufficient ingested vectors, will return some zeros!");
    size_t qLen = q.size(0);
    std::vector<torch::Tensor> ru(qLen);
    std::vector<torch::Tensor> ruTemp;
    if (ingestedVectors >= 1) {
      ruTemp = ParallelIndexWorker::searchTensor(q, ingestedVectors);
    }
    for (size_t i = 0; i < qLen; i++) {
      ru[i] = torch::zeros({k, vecDim});
      if (ingestedVectors >= 1) {
        INTELLI::IntelliTensorOP::editRows(&ru[i], &ruTemp[i], 0);
        //ru[i].slice(0,0,ingestedVectors)=ruTemp[i];
      }
    }
    return ru;
  }

}
