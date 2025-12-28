/*! \file ParallelIndexWorker.cpp*/
//
// Created by tony on 25/05/23.
//

#include <ParallelPartitionIndex/ParallelIndexWorker.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
void CANDY::ParallelIndexWorker::reset() {
  if (myIndexAlgo != nullptr) {
    myIndexAlgo->reset();
  }

}
void CANDY::ParallelIndexWorker::inlineMain() {
  INTELLI_INFO("parallel worker" + std::to_string(myId) + " has started");
  bool shouldLoop = 1;
  int64_t querySeq = 0;
  INTELLI::UtilityFunctions::bind2Core(myId);
  while (shouldLoop) {
    /**
     * @brief 0. offline stages
     */
    while (!m_mut.try_lock());
    while (!buildQueue->empty()) {
      auto buildTensor = *buildQueue->front();
      buildQueue->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->offlineBuild(buildTensor);
      }
      //std::cout<<insertTensor<<std::endl;
    }
    while (!initialLoadQueue->empty()) {
      auto initialLoadTensor = *initialLoadQueue->front();
      initialLoadQueue->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->loadInitialTensor(initialLoadTensor);
      }
      //std::cout<<insertTensor<<std::endl;
    }
    m_mut.unlock();
    while (!initialStrQueue->empty()) {
      while (!m_mut.try_lock());
      auto initialQ = *initialStrQueue->front();
      auto initialLoadTensor = initialQ.t;
      auto initialLoadStr = initialQ.strObj;
      initialStrQueue->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->loadInitialStringObject(initialLoadTensor, initialLoadStr);
      }
      //std::cout<<insertTensor<<std::endl;
      m_mut.unlock();
    }
    /**
      * @brief 1. insert first
      */
    while (!m_mut.try_lock());
    while (!insertQueue->empty()) {
      auto insertTensor = *insertQueue->front();
      insertQueue->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->insertTensor(insertTensor);
        ingestedVectors += insertTensor.size(0);
      }
      //std::cout<<insertTensor<<std::endl;
    }
    while (!insertStrQueue->empty()) {
      auto insertQ = *insertStrQueue->front();
      auto insertTensor = insertQ.t;
      auto insertStr = insertQ.strObj;
      insertStrQueue->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->insertStringObject(insertTensor, insertStr);
        ingestedVectors += insertTensor.size(0);
      }
      //std::cout<<insertTensor<<std::endl;
    }

    /**
    * @brief 2. revise
    */
    while (!reviseQueue0->empty()) {
      auto reviseTensor0 = *reviseQueue0->front();
      reviseQueue0->pop();
      auto reviseTensor1 = *reviseQueue1->front();
      reviseQueue1->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->reviseTensor(reviseTensor0, reviseTensor1);
      }
    }
    /**
    * @brief 3. delete first
   */
    while (!deleteQueue->empty()) {
      auto tip = *deleteQueue->front();
      deleteQueue->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->deleteTensor(tip.t, tip.idx);
      }
    }
    while (!deleteStrQueue->empty()) {
      auto tip = *deleteStrQueue->front();
      deleteStrQueue->pop();
      if (myIndexAlgo != nullptr) {
        myIndexAlgo->deleteStringObject(tip.t, tip.idx);
      }
    }
    m_mut.unlock();
    /**
     * @brief 4. query
     */
    while (!queryQueue->empty()) {
      INTELLI_INFO("Enter query phase");
      auto tip = *queryQueue->front();
      queryQueue->pop();
      if (myIndexAlgo != nullptr) {
        auto tl = myIndexAlgo->searchTensor(tip.t, tip.idx);
        //std::cout<<"worker "+std::to_string(myId)
        TensorListIdxPair tlp(tl, myId, querySeq);
        reduceQueue->push(tlp);
        querySeq++;
        /* int64_t tensors = tip.t.size(0);
         std::vector<torch::Tensor> ru(tensors);
         for (int64_t i = 0; i < tensors; i++) {
           ru[i] = torch::zeros({tip.idx, vecDim});
         }
         TensorListIdxPair tlp(ru,myId,querySeq);
         reduceQueue->push(tlp);*/
      }
    }
    while (!queryStrQueue->empty()) {
      INTELLI_INFO("Enter query phase for string and tensor");
      auto tip = *queryStrQueue->front();
      queryStrQueue->pop();
      if (myIndexAlgo != nullptr) {
        auto tl = myIndexAlgo->searchTensorAndStringObject(tip.t, tip.idx);
        //std::cout<<"worker "+std::to_string(myId)
        auto ruT = std::get<0>(tl);
        auto ruS = std::get<1>(tl);
        TensorStrVecPair tlp(ruT, myId, querySeq, ruS);
        reduceStrQueue->push(tlp);
        querySeq++;
        /* int64_t tensors = tip.t.size(0);
         std::vector<torch::Tensor> ru(tensors);
         for (int64_t i = 0; i < tensors; i++) {
           ru[i] = torch::zeros({tip.idx, vecDim});
         }
         TensorListIdxPair tlp(ru,myId,querySeq);
         reduceQueue->push(tlp);*/
      }
    }
    /**
    * @brief 5. terminate
    */
    while (!cmdQueue->empty()) {
      auto cmd = *cmdQueue->front();
      cmdQueue->pop();
      if (cmd == -1) {
        shouldLoop = false;
        INTELLI_INFO("parallel worker" + std::to_string(myId) + " terminate");
        return;
      }
    }
    // usleep(1000)
  }

}
bool CANDY::ParallelIndexWorker::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  /**
   * @brief 1. find the index algo
   */
  std::string parallelWorker_algoTag = cfg->tryString("parallelWorker_algoTag", "flat", true);
  IndexTable it;
  myIndexAlgo = it.getIndex(parallelWorker_algoTag);
  if (myIndexAlgo == nullptr) {
    return false;
  }
  vecDim = cfg->tryI64("vecDim", 768, true);

  myIndexAlgo->setConfig(cfg);
  /**
   * @brief 2. set up the queues
   */
  int64_t parallelWorker_queueSize = cfg->tryI64("parallelWorker_queueSize", 10, true);
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
  singleWorkerOpt = cfg->tryI64("singleWorkerOpt", 0, true);
  // reduceStrQueue = std::make_shared<INTELLI::SPSCQueue<CANDY::TensorStrVecPair>>((size_t) parallelWorker_queueSize);
  congestionDrop = cfg->tryI64("congestionDrop", 0, true);
  return true;
}
bool CANDY::ParallelIndexWorker::insertTensor(torch::Tensor &t) {
  if (insertQueue->empty() || (!congestionDrop)) {
    insertQueue->push(t);
  } else {
    INTELLI_WARNING("Drop data");
  }
  return true;
}

bool CANDY::ParallelIndexWorker::loadInitialTensor(torch::Tensor &t) {
  if (singleWorkerOpt) {
    INTELLI_WARNING("Optimized for single worker");
    while (!m_mut.try_lock());
    auto ru = myIndexAlgo->loadInitialTensor(t);
    m_mut.unlock();
    return ru;
  }
  initialLoadQueue->push(t);
  return true;
}
bool CANDY::ParallelIndexWorker::deleteTensor(torch::Tensor &t, int64_t k) {
  assert(t.size(1));
  assert(k > 0);
  TensorIdxPair tip(t, k);
  deleteQueue->push(tip);
  return true;
}

bool CANDY::ParallelIndexWorker::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  assert(t.size(1) == w.size(1));
  reviseQueue0->push(t);
  reviseQueue1->push(w);
  return false;
}
std::vector<faiss::idx_t> CANDY::ParallelIndexWorker::searchIndex(torch::Tensor q, int64_t k) {
  if (myIndexAlgo != nullptr) {
    return myIndexAlgo->searchIndex(q, k);
  }

  assert(k > 0);
  assert(q.size(1));
  std::vector<faiss::idx_t> ru(1);
  return ru;
}
void CANDY::ParallelIndexWorker::pushSearch(torch::Tensor q, int64_t k) {
  TensorIdxPair tip(q, k);
  queryQueue->push(tip);
}
void CANDY::ParallelIndexWorker::pushSearchStr(torch::Tensor q, int64_t k) {
  TensorIdxPair tip(q, k);
  queryStrQueue->push(tip);
}
std::vector<torch::Tensor> CANDY::ParallelIndexWorker::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k) {
  if (myIndexAlgo != nullptr) {
    return myIndexAlgo->getTensorByIndex(idx, k);
  }
  assert(k > 0);
  assert(idx.size());
  std::vector<torch::Tensor> ru(1);
  ru[0] = torch::rand({1, 1});
  return ru;
}
torch::Tensor CANDY::ParallelIndexWorker::rawData() {
  if (myIndexAlgo != nullptr) {
    return myIndexAlgo->rawData();
  }
  return torch::rand({1, 1});
}

std::vector<torch::Tensor> CANDY::ParallelIndexWorker::searchTensor(torch::Tensor &q, int64_t k) {
  if (myIndexAlgo != nullptr) {
    if (ingestedVectors > k) {
      return myIndexAlgo->searchTensor(q, k);
    } else {
      INTELLI_ERROR("Insufficient ingested vectors, will return some zeros!");
      size_t qLen = q.size(0);
      std::vector<torch::Tensor> ru(qLen);
      std::vector<torch::Tensor> ruTemp;
      if (ingestedVectors >= 1) {
        ruTemp = myIndexAlgo->searchTensor(q, ingestedVectors);
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
  assert(k > 0);
  assert(q.size(1));
  std::vector<torch::Tensor> ru(1);
  ru[0] = torch::rand({1, 1});
  return ru;
}
bool CANDY::ParallelIndexWorker::startHPC() {
  startThread();
  return true;
}

bool CANDY::ParallelIndexWorker::endHPC() {
  cmdQueue->push(-1);
  return false;
}

bool CANDY::ParallelIndexWorker::offlineBuild(torch::Tensor &t) {
  if (myIndexAlgo != nullptr) {
    buildQueue->push(t);
    return true;
  }
  return false;
}
bool CANDY::ParallelIndexWorker::setFrozenLevel(int64_t frozenLv) {
  if (myIndexAlgo != nullptr) {
    myIndexAlgo->setFrozenLevel(frozenLv);
    return true;
  }
  return false;
}
bool CANDY::ParallelIndexWorker::insertStringObject(torch::Tensor &t, std::vector<std::string> &strs) {
  if (insertStrQueue->empty() || (!congestionDrop)) {
    TensorStrPair tasp(t, -1, strs);
    insertStrQueue->push(tasp);
  } else {
    INTELLI_WARNING("Drop data");
  }
  return true;
}
bool CANDY::ParallelIndexWorker::deleteStringObject(torch::Tensor &t, int64_t k) {
  TensorIdxPair tip(t, k);
  deleteStrQueue->push(tip);
  return true;
}
std::vector<std::vector<std::string>> CANDY::ParallelIndexWorker::searchStringObject(torch::Tensor &q, int64_t k) {
  if (ingestedVectors < k) {
    INTELLI_ERROR("Insufficient ingested vectors, will return some zeros!");
    size_t qLen = q.size(0);
    std::vector<std::vector<std::string>> ru(qLen);
    std::vector<std::vector<std::string>> ruTemp;
    if (ingestedVectors >= 1) {
      ruTemp = myIndexAlgo->searchStringObject(q, ingestedVectors);
    }
    for (size_t i = 0; i < qLen; i++) {
      ru[i] = std::vector<std::string>(k);
      if (ingestedVectors >= 1) {
        //INTELLI::IntelliTensorOP::editRows(&ru[i], &ruTemp[i], 0);
        std::copy(ruTemp[i].begin(), ruTemp[i].end(), ru[i].begin());
        //ru[i].slice(0,0,ingestedVectors)=ruTemp[i];
      }
    }
    return ru;
  }
  return myIndexAlgo->searchStringObject(q, k);
}
std::tuple<std::vector<torch::Tensor>,
           std::vector<std::vector<std::string>>> CANDY::ParallelIndexWorker::searchTensorAndStringObject(torch::Tensor &q,
                                                                                                          int64_t k) {
  if (ingestedVectors < k) {
    INTELLI_ERROR("Insufficient ingested vectors, will return some zeros!");
    size_t qLen = q.size(0);
    std::vector<std::vector<std::string>> ruS(qLen);
    std::vector<torch::Tensor> ruV(qLen);
    std::vector<std::vector<std::string>> ruTempS;
    std::vector<torch::Tensor> ruTempV;
    if (ingestedVectors >= 1) {
      auto tlp = myIndexAlgo->searchTensorAndStringObject(q, ingestedVectors);
      ruTempV = std::get<0>(tlp);
      ruTempS = std::get<1>(tlp);
    }
    for (size_t i = 0; i < qLen; i++) {
      ruS[i] = std::vector<std::string>(k);
      ruV[i] = torch::zeros({k, vecDim});
      if (ingestedVectors >= 1) {
        //INTELLI::IntelliTensorOP::editRows(&ru[i], &ruTemp[i], 0);
        std::copy(ruTempS[i].begin(), ruTempS[i].end(), ruS[i].begin());
        INTELLI::IntelliTensorOP::editRows(&ruV[i], &ruTempV[i], 0);
        //ru[i].slice(0,0,ingestedVectors)=ruTemp[i];
      }
    }
    std::tuple<std::vector<torch::Tensor>, std::vector<std::vector<std::string>>> ruTuple(ruV, ruS);
    return ruTuple;
  }
  return myIndexAlgo->searchTensorAndStringObject(q, k);
}
bool CANDY::ParallelIndexWorker::loadInitialStringObject(torch::Tensor &t, std::vector<std::string> &strs) {
  TensorStrPair tasp(t, -1, strs);
  initialStrQueue->push(tasp);
  return true;
}
