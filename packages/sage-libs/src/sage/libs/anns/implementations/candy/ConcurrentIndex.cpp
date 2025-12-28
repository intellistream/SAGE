/*
 *  Copyright (C) 2024 by the INTELLI team
 *  Created by: Junyao Dong
 *  Created on: 2025/02/11
 *  Description:
 */

#include "ConcurrentIndex.h"
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>

bool CANDY::ConcurrentIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  std::string concurrentlAlgoTag = cfg->tryString("concurrentAlgoTag", "flat", true);
  IndexTable it;
  myIndexAlgo = it.getIndex(concurrentlAlgoTag);
  if (myIndexAlgo == nullptr) {
    return false;
  }

  vecDim = cfg->tryI64("vecDim", 128, true);;
  double writeRatio = cfg->tryDouble("concurrentWriteRatio", 0.5, true);
  int64_t batchSize = cfg->tryI64("concurrentBatchSize", 100, true);
  int64_t numThreads = cfg->tryI64("concurrentNumThreads", 1, true);

  myIndexAlgo->setConfig(cfg);

  return true;
}

bool CANDY::ConcurrentIndex::loadInitialTensor(torch::Tensor &t) {
  auto ru = myIndexAlgo->loadInitialTensor(t);
  return ru;
}

std::vector<SearchRecord> CANDY::ConcurrentIndex::ccInsertAndSearchTensor(torch::Tensor &t,
    torch::Tensor &qt, int64_t k) {
  if (!myIndexAlgo) {
    throw std::runtime_error("Index algorithm not initialized.");
  }

  std::atomic<size_t> commitedOps(0);
  size_t writeTotal = t.size(0);
  size_t searchTotal = qt.size(0);
  std::exception_ptr lastException = nullptr;
  std::mutex lastExceptMutex;
  std::mutex resultMutex;

  std::vector<SearchRecord> searchRes;

  while (commitedOps < writeTotal) {
    size_t insertCnt = std::min(batchSize, static_cast<int64_t>(writeTotal - commitedOps.load()));
    size_t searchCnt = insertCnt / writeRatio;

    std::atomic<size_t> currentInsert(0);
    std::vector<std::thread> writeThreads;

    for (size_t i = 0; i < numThreads; i++) {
      writeThreads.emplace_back([&, i] {
        while (true) {
          size_t idx = currentInsert.fetch_add(1);
          if (idx >= insertCnt) break;
          size_t gIdx = commitedOps.fetch_add(1);
          if (gIdx >= writeTotal) break;
          try {
            auto in = t[gIdx];
            myIndexAlgo->insertTensor(in);
          } catch (...) {
            std::unique_lock<std::mutex> lock(lastExceptMutex);
            lastException = std::current_exception();
          }
        }
      });
    }

    std::atomic<size_t> currentSearch(0);
    std::vector<std::thread> readThreads;
    std::vector<std::vector<SearchRecord>> localRes(numThreads);

    for (size_t i = 0; i < numThreads; i++) {
      readThreads.emplace_back([&, i] {
        std::vector<SearchRecord> threadRes;
        while (true) {
          size_t idx = currentSearch.fetch_add(1);
          if (idx >= searchCnt) break;
          size_t queryIdx = std::rand() % searchTotal;
          try {
            auto q = qt[queryIdx];
            auto res = myIndexAlgo->searchTensor(q, k);
            threadRes.emplace_back(commitedOps.load(), queryIdx, res);
          } catch (...) {
            std::unique_lock<std::mutex> lock(lastExceptMutex);
            lastException = std::current_exception();
          }
        }
        localRes[i] = std::move(threadRes);
      });
    }

    for (auto &t : writeThreads) {
      t.join();
    }
    writeThreads.clear();

    for (auto &t : readThreads) {
      t.join();
    }
    readThreads.clear();

    {
      std::unique_lock<std::mutex> lock(resultMutex);
      for (const auto& res : localRes) {
        searchRes.insert(searchRes.end(), res.begin(), res.end());
      }
    }
  }

  if (lastException) {
    std::rethrow_exception(lastException);
  }

  return searchRes;
}

std::vector<torch::Tensor> CANDY::ConcurrentIndex::searchTensor(torch::Tensor &q, int64_t k) {
  return myIndexAlgo->searchTensor(q, k);
}

void CANDY::ConcurrentIndex::reset() {

}
