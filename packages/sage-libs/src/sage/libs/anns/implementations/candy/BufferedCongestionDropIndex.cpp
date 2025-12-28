/*! \file BufferedCongestionDropIndex.cpp*/
//


#include <BufferedCongestionDropIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
INTELLI::ConfigMapPtr CANDY::BufferedCongestionDropIndex::generateBucketedFlatIndexConfig(INTELLI::ConfigMapPtr cfg) {
  auto ru = newConfigMap();
  ru->edit("initialVolume", cfg->tryI64("buffer_initialVolume", 1000, true));
  ru->edit("expandStep", cfg->tryI64("buffer_expandStep", 100, true));
  ru->edit("numberOfBuckets", cfg->tryI64("buffer_numberOfBuckets", 1, true));
  ru->edit("bucketMode", cfg->tryString("buffer_bucketMode", "mean", true));
  ru->edit("quantizationMax", cfg->tryDouble("buffer_quantizationMax", 1.0, true));
  ru->edit("quantizationMin", cfg->tryDouble("buffer_quantizationMin", -1.0, true));
  ru->edit("encodeLen", cfg->tryI64("buffer_encodeLen", 1, true));
  ru->edit("lshMatrixType", cfg->tryString("buffer_lshMatrixType", "gaussian", true));
  return ru;
}
bool CANDY::BufferedCongestionDropIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  vecDim = cfg->tryI64("vecDim", 768, true);
  bufferProbability = cfg->tryDouble("bufferProbability", 0.5, true);
  if (bufferProbability > 1 || bufferProbability < 0) {
    bufferProbability = 1.1;
    INTELLI_WARNING("I'll route everything to buffer");
  }
  randGen = std::mt19937_64(775);
  bufferPart = newBucketedFlatIndex();
  bufferPart->setConfig(generateBucketedFlatIndexConfig(cfg));
  aknnPart = newCongestionDropIndex();
  aknnPart->setConfig(cfg);
  randDistribution = std::uniform_real_distribution<double>(0.0, 1.0);
  return true;
}
void CANDY::BufferedCongestionDropIndex::reset() {
  bufferPart->reset();
  aknnPart->reset();
}
bool CANDY::BufferedCongestionDropIndex::startHPC() {
  return aknnPart->startHPC();
}

bool CANDY::BufferedCongestionDropIndex::endHPC() {
  return aknnPart->endHPC();
}

bool CANDY::BufferedCongestionDropIndex::setFrozenLevel(int64_t frozenLv) {
  return aknnPart->setFrozenLevel(frozenLv);
}
bool CANDY::BufferedCongestionDropIndex::offlineBuild(torch::Tensor &t) {
  return aknnPart->offlineBuild(t);
}
bool CANDY::BufferedCongestionDropIndex::loadInitialTensor(torch::Tensor &t) {
  return aknnPart->loadInitialTensor(t);
}
bool CANDY::BufferedCongestionDropIndex::insertTensorInline(torch::Tensor &t) {
  double rv = randDistribution(randGen);
  if (rv < bufferProbability) {
    bufferPart->insertTensor(t);
  } else {
    aknnPart->insertTensor(t);
  }
  return true;
}
bool CANDY::BufferedCongestionDropIndex::insertTensor(torch::Tensor &t) {
  if (maxDataPiece < 0 || maxDataPiece > t.size(0)) {
    return insertTensorInline(t);
  } else {
    int64_t startRow = 0;
    int64_t endRow = maxDataPiece;
    int64_t allRows = t.size(0);
    while (startRow < allRows) {
      auto pieceI = t.slice(0, startRow, endRow);
      startRow += maxDataPiece;
      endRow += maxDataPiece;
      if (endRow > allRows) {
        endRow = allRows;
      }
      insertTensorInline(pieceI);
    }
  }
  return true;
}

bool CANDY::BufferedCongestionDropIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  size_t tensors = (size_t) t.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  std::vector<torch::Tensor> ruBuffer = bufferPart->searchTensor(t, k);
  std::vector<torch::Tensor> ruAKNN = aknnPart->searchTensor(t, k);
  std::vector<torch::Tensor> ru(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * 2, vecDim});
    ru[i] = torch::zeros({k, vecDim});
    ruTemp[i].slice(0, 0, k) = ruBuffer[i];
    ruTemp[i].slice(0, k, k * 2) = ruAKNN[i];
  }
  /**
  * @brief 2. reduce
  */
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto queryTensor = t.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * 2, dbData); // add vectors to the index
    int64_t querySize = 1;
    std::vector<faiss::idx_t> idxRu(k * querySize);
    std::vector<float> distance(k * querySize);
    indexFlat.search(querySize, queryData, k, distance.data(), idxRu.data());
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idxRu[j];
      int64_t workerNo = tempIdx / k;
      auto tensorToDelete = dbTensor.slice(0, tempIdx, tempIdx + 1);
      if (workerNo == 0) {
        bufferPart->deleteTensor(tensorToDelete, 1);
      } else {
        aknnPart->deleteTensor(tensorToDelete, 1);
      }
      INTELLI_INFO("tell worker" + std::to_string(workerNo) + " to delete tensor");
      // if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1); }
    }
  }
  return true;
}

bool CANDY::BufferedCongestionDropIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  //assert(t.size(1) == w.size(1));
  /**
   * @brief only allow to delete and insert, no straightforward revision
   */
  deleteTensor(t, 1);
  insertTensor(w);
  return true;
}

std::vector<torch::Tensor> CANDY::BufferedCongestionDropIndex::searchTensor(torch::Tensor &q, int64_t k) {
  size_t tensors = (size_t) q.size(0);
  std::vector<torch::Tensor> ruTemp(tensors);
  std::vector<torch::Tensor> ruBuffer = bufferPart->searchTensor(q, k);
  std::vector<torch::Tensor> ruAKNN = aknnPart->searchTensor(q, k);
  std::vector<torch::Tensor> ru(tensors);
  for (size_t i = 0; i < tensors; i++) {
    ruTemp[i] = torch::zeros({k * 2, vecDim});
    ru[i] = torch::zeros({k, vecDim});
    ruTemp[i].slice(0, 0, k) = ruBuffer[i];
    ruTemp[i].slice(0, k, k * 2) = ruAKNN[i];
  }
  for (size_t i = 0; i < tensors; i++) {
    faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
    auto dbTensor = ruTemp[i].contiguous();
    auto queryTensor = q.slice(0, i, i + 1).contiguous();
    float *dbData = dbTensor.data_ptr<float>();
    float *queryData = queryTensor.contiguous().data_ptr<float>();
    indexFlat.add(k * 2, dbData); // add vectors to the index
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
