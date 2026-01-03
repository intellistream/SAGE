//
// Created by tony on 24/05/23.
//

#include <Parallelization/BlockPartitionRunner.h>
#include <Utils/UtilityFunctions.h>
#include "Utils/ThreadPerf.hpp"

using namespace INTELLI;

void LibAMM::BlockPartitionWorker::setConfig(INTELLI::ConfigMapPtr _cfg) {
  cfg = _cfg;
  sketchDimension = cfg->tryU64("sketchDimension", 50, true);
  osScheduling = cfg->tryU64("osScheduling", 0, false);
  std::string ptFile = cfg->tryString("ptFile", "torchscripts/FDAMM.pt", true);
  useCPP = cfg->tryU64("useCPP", 0, true);
  if (useCPP) {
    std::string cppAlgoTag = cfg->tryString("cppAlgoTag", "mm", true);
    cppAlgoPtr = cppAlgoTable.findCppAlgo(cppAlgoTag);
    cppAlgoPtr->setConfig(_cfg);
  }
  if (!useCPP || (cppAlgoPtr == nullptr)) {
    module = torch::jit::load(ptFile);
    if (useCPP) {
      INTELLI_ERROR("No cpp algorithm found, go back to pt module");
      useCPP = 0;
    }
  }

}

void LibAMM::BlockPartitionWorker::setWorkParameters(uint64_t aStart, uint64_t aEnd, int mycore) {
  startRow = aStart;
  endRow = aEnd;
  coreBind = mycore;
  //matC=newTensor(torch::zeros({(long)(endRow+1-startRow),matB->size(1)}));


}

void LibAMM::BlockPartitionWorker::setABC(LibAMM::TensorPtr A, LibAMM::TensorPtr B, LibAMM::TensorPtr C) {
  matA = A;
  matB = B;
  matC = C;
  //assert(C);
}

void LibAMM::BlockPartitionWorker::inlineMain() {
    //std::cout<<"thread at "+ to_string(coreBind)+" start\r\n";
    /**
     * @brief 1. bind core and torch setting
     */
    if (!osScheduling) {
        INTELLI::UtilityFunctions::bind2Core((int) coreBind);
    }
    torch::set_num_threads(1);
    /**
     * @brief 2. multiply sub-matrix of A
     */

    //torch::Tensor
    //torch::Tensor subC =  module.forward({subA, *matB, (long) sketchDimension}).toTensor();
    // Copy the results back to the output matrix C
    //matC->slice(0, startRow, endRow) = subC;
    subA = matA->slice(0, startRow, endRow);
    ThreadPerf pef(coreBind);
    pef.setPerfList();
    pef.start();
    //irC=module.forward({subA, *matB, (long) sketchDimension}).toTensor();
    if (useCPP) {
        INTELLI_WARNING("USE CPP ALGO");
        matC->slice(0, startRow, endRow) = cppAlgoPtr->amm(subA, *matB, sketchDimension);
    } else {
        matC->slice(0, startRow, endRow) =module.forward({subA, *matB, (long) sketchDimension}).toTensor();
    }
    pef.end();
    pefResult = pef.resultToConfigMap();
    //std::cout<<subC;
}

INTELLI::ConfigMapPtr LibAMM::BlockPartitionWorker::getBreakDown() {
  if (useCPP && cppAlgoPtr) {
    return cppAlgoPtr->getBreakDown();
  }
  return nullptr;
}

uint64_t LibAMM::BlockPartitionWorker::getElapsedTime() {
    return pefResult->getU64("perfElapsedTime");
}

INTELLI::ConfigMapPtr LibAMM::BlockPartitionWorker::getPefResult(){
    return pefResult;
};

void LibAMM::BlockPartitionRunner::setConfig(INTELLI::ConfigMapPtr _cfg) {
  cfg = _cfg;
  threads = cfg->tryU64("threads", 2, true);
  workers = std::vector<BlockPartitionWorkerPtr>(threads);
  firstCoreBind = cfg->tryU64("coreBind", 0, false);
  for (uint64_t i = 0; i < threads; i++) {
    workers[i] = newBlockPartitionWorker();
    workers[i]->setConfig(cfg);
  }

  INTELLI_INFO("set up " + to_string(threads) + "workers.");
}

void LibAMM::BlockPartitionRunner::createABC(torch::Tensor A, torch::Tensor B) {

  matA = newTensor(A);
  matB = newTensor(B);
  matC = newTensor(torch::zeros({A.size(0), B.size(1)}));
  for (uint64_t i = 0; i < threads; i++) {
    uint64_t rows_per_worker = A.size(0) / threads;
    uint64_t start_row = i * rows_per_worker;
    uint64_t end_row = (i == threads - 1) ? A.size(0) : start_row + rows_per_worker;
    workers[i]->setABC(matA, matB, matC);
    workers[i]->setWorkParameters(start_row, end_row, firstCoreBind + i);
    INTELLI_INFO("thread " + to_string(i) + " is bound to core " + to_string(firstCoreBind + i));
  }
}

torch::Tensor LibAMM::BlockPartitionRunner::parallelForward() {
    for (uint64_t i = 0; i < threads; i++) {
        workers[i]->startThread();
    }
    INTELLI_INFO("start " + to_string(threads) + "workers.");
    for (uint64_t i = 0; i < threads; i++) {
        workers[i]->joinThread();
    }
    /* for(uint64_t i=0;i<threads;i++)
     {
       matC->slice(0, workers[i]->startRow, workers[i]->endRow) = workers[i]->irC;
     }*/
    return *matC;
}

torch::Tensor LibAMM::BlockPartitionRunner::runAMM(torch::Tensor A, torch::Tensor B) {
    createABC(A, B);
    parallelForward();
    calculateMetrics();
    return *matC;
}

uint64_t LibAMM::BlockPartitionRunner::getElapsedTime() {
  uint64_t ti = 0;
  uint64_t tMax = 0;
  for (uint64_t i = 0; i < threads; i++) {
    ti = workers[i]->getElapsedTime();
    if (ti > tMax) {
      tMax = ti;
    }
  }
  return tMax;
}

void LibAMM::BlockPartitionRunner::appendThreadInfo(INTELLI::ConfigMapPtr ru) {
  for (uint64_t i = 0; i < threads; i++) {
    std::string keyElapesedTime = "thread" + to_string(i) + "RunTime";
    ru->edit(keyElapesedTime, (uint64_t) workers[i]->getElapsedTime());
  }
}

void LibAMM::BlockPartitionRunner::calculateMetrics() {
    ConfigMap allThreadPefResult;
    ConfigMap singleThreadperResult;
    for (uint64_t i = 0; i < threads; i++) {
        workers[i]->getPefResult()->cloneInto(singleThreadperResult);
        singleThreadperResult.addPrefixToKeys("thread" + to_string(i));
        singleThreadperResult.cloneInto(allThreadPefResult);
    }
    metrics = std::make_shared<ConfigMap>(allThreadPefResult);
    uint64_t elapsedTime = getElapsedTime(); // max thread time among all threads
    metrics->edit("perfElapsedTime", elapsedTime);
    double throughput = (matA->size(0) * 1e6) / metrics->getU64("perfElapsedTime");
    metrics->edit("throughput", throughput);
    metrics->edit("throughputByElements", (double) (throughput * matA->size(1)));
}

INTELLI::ConfigMapPtr LibAMM::BlockPartitionRunner::getMetrics() {
    return metrics;
}

INTELLI::ConfigMapPtr LibAMM::BlockPartitionRunner::getBreakDown() {
  return workers[0]->getBreakDown();
}
