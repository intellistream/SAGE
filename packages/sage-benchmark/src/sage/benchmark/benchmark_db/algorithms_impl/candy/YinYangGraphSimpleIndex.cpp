//
// Created by tony on 06/02/24.
//
/*! \file YinYangGraphSimpleIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <YinYangGraphSimpleIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>

bool CANDY::YinYangGraphSimpleIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  vecDim = cfg->tryI64("vecDim", 768, true);
  maxConnection = cfg->tryI64("maxConnection", 256, true);

  candidateTimes = cfg->tryI64("candidateTimes", 1, true);

  return true;

}

bool CANDY::YinYangGraphSimpleIndex::insertSingleRowTensor(torch::Tensor &t) {
  if (startPoint == nullptr) {
    startPoint = newYinYangVertex();
    startPoint->init(t, 0, maxConnection, 1, true);
  } else {
    auto dataPoint = newYinYangVertex();
    dataPoint->init(t, 0, maxConnection, 1, true);
    auto ep = CANDY::YinYangVertex::greedySearchForNearestVertex(dataPoint, startPoint);
    auto closestInNewConVertexLv =
        CANDY::YinYangVertex::greedySearchForKNearestVertex(dataPoint, ep, maxConnection, false, false);
    for (auto &iter : closestInNewConVertexLv) {

      CANDY::YinYangVertex::tryToConnect(dataPoint, iter, vertexMapGe1Vec);
    }
  }
  return true;
}
bool CANDY::YinYangGraphSimpleIndex::insertTensor(torch::Tensor &t) {
  int64_t rows = t.size(0);
  for (int64_t i = 0; i < rows; i++) {
    auto rowI = t.slice(0, i, i + 1);
    insertSingleRowTensor(rowI);
  }
  return true;
}

std::vector<torch::Tensor> CANDY::YinYangGraphSimpleIndex::searchTensor(torch::Tensor &q, int64_t k) {
  int64_t rows = q.size(0);
  std::vector<torch::Tensor> ru((size_t) rows);
  for (int64_t i = 0; i < rows; i++) {
    ru[i] = torch::zeros({k, vecDim});
  }

  //std::cout<<qr<<std::endl;
  //exit(-1);
  //auto qr= randomProjection(q);
  for (int64_t i = 0; i < rows; i++) {
    auto rowI = q.slice(0, i, i + 1);
    std::cout << rowI.slice(1, 0, 2) << std::endl;
    //exit(-1);
    auto candidateTensor = CANDY::YinYangVertex::greedySearchForKNearestTensor(rowI, startPoint, k * candidateTimes);
    if (candidateTensor.size(0) > k) {
      // std::cout<<"candidate tensor is \n"<<candidateTensor<<std::endl;
      // return ru;
      faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
      auto dbTensor = candidateTensor.contiguous();
      auto queryTensor = rowI.contiguous();
      float *dbData = dbTensor.data_ptr<float>();
      float *queryData = queryTensor.contiguous().data_ptr<float>();
      indexFlat.add(dbTensor.size(0), dbData); // add vectors to the index
      int64_t querySize = 1;
      std::vector<faiss::idx_t> idxRu(k * querySize);
      std::vector<float> distance(k * querySize);
      indexFlat.search(querySize, queryData, k, distance.data(), idxRu.data());
      //return ru;
      for (int64_t j = 0; j < k; j++) {
        int64_t tempIdx = idxRu[j];
        if (tempIdx >= 0) {
          ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1);
          // std::cout<<"idx "<<tempIdx<<std::endl;
        }
      }
    } else {
      ru[i] = candidateTensor;
    }

  }
  return ru;
}
