/*! \file OnlinePQIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <OnlinePQIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
bool CANDY::OnlinePQIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  vecDim = cfg->tryI64("vecDim", 768, true);
  coarseGrainedClusters = cfg->tryI64("coarseGrainedClusters", 4096, true);
  subQuantizers = cfg->tryI64("subQuantizers", 8, true);
  coarseGrainedBuiltPath = cfg->tryString("coarseGrainedBuiltPath", "OnlinePQIndex_coarse.rbt", true);
  fineGrainedBuiltPath = cfg->tryString("fineGrainedBuiltPath", "OnlinePQIndex_fine.rbt", true);
  fineGrainedClusters = cfg->tryI64("fineGrainedClusters", 256, true);
  cudaBuild = cfg->tryI64("cudaBuild", 0, true);
  maxBuildIteration = cfg->tryI64("maxBuildIteration", 1000, true);
  candidateTimes = cfg->tryI64("candidateTimes", 1, true);
  disableADC = cfg->tryI64("disableADC", 0, true);
  lastNNZ = -1;
  if (disableADC) {
    INTELLI_WARNING("running under IVFPQ");
  } else {
    INTELLI_WARNING("running under IVFADC");
  }

  if (subQuantizers > vecDim) {
    subQuantizers = vecDim;
  }
  if (fineGrainedClusters > 256 || fineGrainedClusters < 0) {
    fineGrainedClusters = 256;
  }
  IVFList.init(coarseGrainedClusters, subQuantizers);
  /**
   * @brief create cluster instances
   */
  coarseQuantizerPtr = newSimpleStreamClustering();
  fineQuantizerPtrs = std::vector<SimpleStreamClusteringPtr>((size_t) subQuantizers);
  for (int64_t i = 0; i < subQuantizers; i++) {
    fineQuantizerPtrs[i] = newSimpleStreamClustering();
  }
  isBuilt = tryLoadQuantizers();
  if (!isBuilt) {
    INTELLI_WARNING("the PQ data structure is not loaded, please build it first");
  }

  return true;
}
bool CANDY::OnlinePQIndex::tryLoadQuantizers() {

  torch::Tensor coarseTenor, fineTensor;
  subQuantizerStartPos = std::vector<int64_t>((size_t) subQuantizers);
  subQuantizerEndPos = std::vector<int64_t>((size_t) subQuantizers);
  int64_t step = vecDim / subQuantizers;
  subQuantizerStartPos[0] = 0;
  subQuantizerEndPos[subQuantizers - 1] = vecDim;
  int64_t stepAcc = step;
  for (int64_t i = 1; i < subQuantizers; i++) {
    subQuantizerStartPos[i] = stepAcc;
    stepAcc += step;
  }
  stepAcc = step;
  for (int64_t i = 0; i < subQuantizers - 1; i++) {
    subQuantizerEndPos[i] = stepAcc;
    stepAcc += step;
  }
  bool loaded = INTELLI::IntelliTensorOP::tensorFromFile(&coarseTenor, coarseGrainedBuiltPath);
  if (!loaded) {
    INTELLI_ERROR("error in loading coarse grained centroid, abort");
    return false;
  }
  loaded = INTELLI::IntelliTensorOP::tensorFromFile(&fineTensor, fineGrainedBuiltPath);
  if (!loaded) {
    INTELLI_ERROR("error in loading fine grained centroid, abort");
    return false;
  }
  if (coarseTenor.size(1) != vecDim || fineTensor.size(1) != vecDim) {
    INTELLI_ERROR("invalid dimension, abort");
    return false;
  }
  coarseQuantizerPtr->loadCentroids(coarseTenor);

  for (int64_t i = 0; i < subQuantizers; i++) {
    auto subTensor = fineTensor.slice(1, subQuantizerStartPos[i], subQuantizerEndPos[i]);
    INTELLI_INFO("sub quantizer " + std::to_string(i) + ", col " + std::to_string(subQuantizerStartPos[i]) + "to"
                     + std::to_string(subQuantizerEndPos[i]));
    fineQuantizerPtrs[i]->loadCentroids(subTensor);
  }
  return true;

}
bool CANDY::OnlinePQIndex::loadInitialTensor(torch::Tensor &t) {
  if (!isBuilt) {
    INTELLI_WARNING("the PQ data structure is not loaded, automatically build it first");
    offlineBuild(t);
  }
  int64_t oldFrozenLevel = frozenLevel;
  setFrozenLevel(0);
  insertTensor(t);
  setFrozenLevel(oldFrozenLevel);
  return true;
}
bool CANDY::OnlinePQIndex::offlineBuild(torch::Tensor &t) {
  /**
   * @brief 1. build the coarse-grained clusters
   */
  if (t.size(1) != vecDim) {
    return false;
  }
  bool cudaBool = false;
  if (cudaBuild) {
    cudaBool = true;
    INTELLI_WARNING("using cuda to build");
  }
  coarseQuantizerPtr->buildCentroids(t,
                                     coarseGrainedClusters,
                                     maxBuildIteration,
                                     SimpleStreamClustering::euclideanDistance,
                                     cudaBool);
  coarseQuantizerPtr->saveCentroidsToFile(coarseGrainedBuiltPath);
  //return false;
  INTELLI_INFO("build coarse grained is done");
  /**
  * @brief 2. calculate the residential
  */
  torch::Tensor residentialTensor;
  int64_t rows = t.size(0);
  auto lables = coarseQuantizerPtr->classifyMultiRow(t);
  auto coarseCentroids = coarseQuantizerPtr->exportCentroids();
  if (disableADC) {
    residentialTensor = t.clone();
  } else {
    residentialTensor = torch::zeros({t.size(0), t.size(1)});
    for (int64_t i = 0; i < rows; i++) {
      residentialTensor.slice(0, i, i + 1) = coarseCentroids.slice(0, lables[i], lables[i] + 1);
    }
    residentialTensor = t - residentialTensor;
  }
  auto fineCentroids = torch::zeros({fineGrainedClusters, t.size(1)});
  /**
   * @brief 3. build sub quantizers
   */
  for (int64_t i = 0; i < subQuantizers; i++) {
    auto subTensor = residentialTensor.slice(1, subQuantizerStartPos[i], subQuantizerEndPos[i]);
    fineQuantizerPtrs[i]->buildCentroids(subTensor,
                                         fineGrainedClusters,
                                         maxBuildIteration,
                                         SimpleStreamClustering::euclideanDistance,
                                         cudaBool);
    fineCentroids.slice(1, subQuantizerStartPos[i], subQuantizerEndPos[i]) = fineQuantizerPtrs[i]->exportCentroids();
    INTELLI_INFO(std::to_string(i) + "th fine grained is done");
  }
  INTELLI_INFO("all fine grained is done");
  INTELLI::IntelliTensorOP::tensorToFile(&fineCentroids, fineGrainedBuiltPath);
  isBuilt = true;
  return true;
}
std::vector<int64_t> CANDY::OnlinePQIndex::coarseGrainedEncode(torch::Tensor &t, torch::Tensor *residential) {
  int64_t rows = t.size(0);
  auto lables = coarseQuantizerPtr->classifyMultiRow(t);
  auto coarseCentroids = coarseQuantizerPtr->exportCentroids();
  if (disableADC) {
    *residential = t.clone();
  } else {
    auto residentialTensor = torch::zeros(t.sizes());
    for (int64_t i = 0; i < rows; i++) {
      residentialTensor.slice(0, i, i + 1) = coarseCentroids.slice(0, lables[i], lables[i] + 1);
      /*if(frozenLevel!=0)
      {
        coarseQuantizerPtr->addSingleRow(t.slice(0,i,i+1),frozenLevel);
      }*/
    }
    *residential = t - residentialTensor;
  }
  return lables;
}
std::vector<std::vector<uint8_t>> CANDY::OnlinePQIndex::fineGrainedEncode(torch::Tensor &residential) {
  int64_t rows = residential.size(0);
  std::vector<std::vector<uint8_t>> ru((size_t) rows);
  std::vector<std::vector<int64_t>> subClusterIdx((size_t) subQuantizers);
  /**
   * @brief 1. get the output of each subquantizer
   */
  for (int64_t i = 0; i < subQuantizers; i++) {
    auto subTensor = residential.slice(1, subQuantizerStartPos[i], subQuantizerEndPos[i]);
    subClusterIdx[i] = fineQuantizerPtrs[i]->classifyMultiRow(subTensor);
    /* if(frozenLevel!=0)
     {
       for(int64_t j=0;j<rows;j++)
       {
         fineQuantizerPtrs[i]->addSingleRow(subTensor.slice(0,j,j+1));
       }
     }*/
  }
  for (int64_t i = 0; i < rows; i++) {
    ru[i] = std::vector<uint8_t>((size_t) subQuantizers);
    for (int64_t j = 0; j < subQuantizers; j++) {
      ru[i][j] = ((subClusterIdx[j][i]) & 255);
    }

  }
  return ru;
}
void CANDY::OnlinePQIndex::reset() {
  lastNNZ = -1;
}
bool CANDY::OnlinePQIndex::insertTensor(torch::Tensor &t) {
  if (!isBuilt) {
    return false;
  }
  torch::Tensor residential;
  auto coarseBkt = coarseGrainedEncode(t, &residential);
  auto fineEncode = fineGrainedEncode(residential);
  int64_t rows = t.size(0);
  for (int64_t i = 0; i < rows; i++) {
    auto rowI = t.slice(0, i, i + 1);
    IVFList.insertTensorWithEncode(rowI, fineEncode[i], (uint64_t) coarseBkt[i]);
    if (frozenLevel > 0 && frozenLevel != 2) {
      coarseQuantizerPtr->addSingleRowWithIdx(rowI, coarseBkt[i], 1);
    }
    if (frozenLevel > 1) {
      auto residentialI = residential.slice(0, i, i + 1);
      for (int64_t j = 0; j < subQuantizers; j++) {
        auto subTensor = residentialI.slice(1, subQuantizerStartPos[j], subQuantizerEndPos[j]);
        int64_t fineIdx = fineEncode[i][j];
        fineQuantizerPtrs[j]->addSingleRowWithIdx(subTensor, fineIdx, 1);
      }
    }

  }
  return true;
}
bool CANDY::OnlinePQIndex::deleteRowsInline(torch::Tensor &t) {
  int64_t rows = t.size(0);
  torch::Tensor residential;
  auto coarseBkt = coarseGrainedEncode(t, &residential);
  auto fineEncode = fineGrainedEncode(residential);
  for (int64_t i = 0; i < rows; i++) {
    auto rowI = t.slice(0, i, i + 1);

    IVFList.deleteTensorWithEncode(rowI, fineEncode[i], (uint64_t) coarseBkt[i]);
    if (frozenLevel > 0 && frozenLevel != 2) {
      coarseQuantizerPtr->deleteSingleRowWithIdx(rowI, coarseBkt[i], 1);
    }
    if (frozenLevel > 1) {
      auto residentialI = residential.slice(0, i, i + 1);
      for (int64_t j = 0; j < subQuantizers; j++) {
        auto subTensor = residentialI.slice(1, subQuantizerStartPos[j], subQuantizerEndPos[j]);
        int64_t fineIdx = fineEncode[i][j];
        fineQuantizerPtrs[j]->deleteSingleRowWithIdx(subTensor, fineIdx, 1);
      }
    }

  }
  return true;
}
bool CANDY::OnlinePQIndex::deleteTensor(torch::Tensor &q, int64_t k) {
  auto annsRu = searchTensor(q, k);
  size_t tensors = annsRu.size();
  for (size_t i = 0; i < tensors; i++) {
    deleteRowsInline(annsRu[i]);
  }
  return true;
}

bool CANDY::OnlinePQIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  deleteTensor(t, 1);
  insertTensor(w);
  return true;
}

std::vector<torch::Tensor> CANDY::OnlinePQIndex::searchTensor(torch::Tensor &q, int64_t k) {
  int64_t rows = q.size(0);
  torch::Tensor residential;
  auto coarseBkt = coarseGrainedEncode(q, &residential);
  auto fineEncode = fineGrainedEncode(residential);
  std::vector<torch::Tensor> ru((size_t) rows);
  for (int64_t i = 0; i < rows; i++) {
    ru[i] = torch::zeros({k, vecDim});
  }
  for (int64_t i = 0; i < rows; i++) {
    auto rowI = q.slice(0, i, i + 1);
    auto candidateTensor =
        IVFList.getMinimumNumOfTensors(rowI, fineEncode[i], (uint64_t) coarseBkt[i], k * candidateTimes);
    if (candidateTensor.size(0) > k) {
      // std::cout<<"candidate tensor is \n"<<candidateTensor<<std::endl;
      // return ru;
      faiss::IndexFlat indexFlat(vecDim); // call constructor
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

bool CANDY::OnlinePQIndex::setFrozenLevel(int64_t frozenLv) {
  frozenLevel = frozenLv;
  return true;
}
