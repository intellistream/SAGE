/*! \file BucketedFlatIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include "BucketedFlatIndex.h"
#include "Utils/UtilityFunctions.h"
#include <time.h>
#include <chrono>
#include <assert.h>

static inline uint32_t nnzBits(uint32_t a) {
  if (a == 0) {
    return 1;
  }
  return 32 - __builtin_clz(a);
}
#ifndef BF_NEXT_POW_2
/**
 *  compute the next number, greater than or equal to 32-bit unsigned v.
 *  taken from "bit twiddling hacks":
 *  http://graphics.stanford.edu/~seander/bithacks.html
 */
#define BF_NEXT_POW_2(V)                           \
    do {                                        \
        V--;                                    \
        V |= V >> 1;                            \
        V |= V >> 2;                            \
        V |= V >> 4;                            \
        V |= V >> 8;                            \
        V |= V >> 16;                           \
        V++;                                    \
    } while(0)
#endif

#ifndef HASH
#define HASH(X, MASK, SKIP) (((X) & MASK) >> SKIP)
#endif

static inline torch::Tensor genLshMatrix(int64_t N, int64_t D, std::string tag) {
  torch::Tensor ru;
  if (tag == "gaussian") {
    ru = torch::randn({N, D});
  } else {
    ru = torch::rand({N, D}) - 0.5;
  }
  return ru;
}
bool CANDY::BucketedFlatIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  /**
   * @breif 1. common init
   */
  vecDim = cfg->tryI64("vecDim", 768, true);
  initialVolume = cfg->tryI64("initialVolume", 1000, true);
  expandStep = cfg->tryI64("expandStep", 100, true);
  numberOfBuckets = cfg->tryI64("numberOfBuckets", 1, true);
  if (numberOfBuckets < 0) {
    numberOfBuckets = 1;
  }

  if (numberOfBuckets > 1) {
    size_t bks = numberOfBuckets;
    BF_NEXT_POW_2(bks);
    numberOfBuckets = bks;
    INTELLI_INFO("Note, adjust the number of buckets into" + std::to_string(numberOfBuckets));
    uint32_t tb = numberOfBuckets;
    bucketsLog2 = nnzBits(tb);
  }
  buckets = std::vector<FlatIndexPtr>((size_t) numberOfBuckets);
  for (size_t i = 0; i < (size_t) numberOfBuckets; i++) {
    buckets[i] = newFlatIndex();
    buckets[i]->setConfig(cfg);
  }

  std::string bucketMode = cfg->tryString("bucketMode", "mean", true);

  /**
   * @breif 2.a init of mean mode
   */
  if (bucketMode == "mean") {
    bucketModeNumber = 0;
    INTELLI_INFO("Using quantized mean to assign buckets");
    quantizationMax = cfg->tryDouble("quantizationMax", 1.0, true);
    quantizationMin = cfg->tryDouble("quantizationMin", -1.0, true);
  } else if (bucketMode == "ML") {
    bucketModeNumber = 2;
    INTELLI_INFO("Using ML to assign buckets");
    myMLModel = newMLPBucketIdxModel();
    myMLModel->init(vecDim, numberOfBuckets, cfg);
    buildingSamples = cfg->tryI64("buildingSamples", cfg->tryI64("sampleRows", 2048, true), true);
    buildingANNK = cfg->tryI64("buildingANNK", 10, true);
  }
    /**
   * @breif 2.a init of lsh mode
   */
  else {
    bucketModeNumber = 1;
    INTELLI_INFO("Using lsh to assign buckets");
    encodeLen = cfg->tryI64("encodeLen", 1, true);
    std::string lshMatrixType = cfg->tryString("lshMatrixType", "gaussian", true);
    rotationMatrix = genLshMatrix(vecDim, encodeLen * 8, lshMatrixType);
  }

  //dbTensor = torch::zeros({initialVolume, vecDim});
  return true;
}
uint64_t CANDY::BucketedFlatIndex::encodeSingleRowMean(torch::Tensor &tensor) {
  double value = torch::mean(tensor).item<double>();
  double minBound = quantizationMin;
  double maxBound = quantizationMax;
  if (value < minBound || value > maxBound) {
    std::cerr << "Error: Value outside the specified bounds." << std::endl;
    return 0; // or handle the error as needed
  }
  double stepSize = (maxBound - minBound) / numberOfBuckets;
  int64_t quantizationCode = static_cast<int64_t>((value - minBound) / stepSize);
  return static_cast<uint64_t>(quantizationCode);
}
uint64_t CANDY::BucketedFlatIndex::encodeSingleRowLsh(torch::Tensor &tensor) {
  uint64_t bktRu = 0;
  std::vector<uint8_t> ru((size_t) encodeLen, 0);
  float *rawFloat = tensor.contiguous().data_ptr<float>();
  size_t bitMax = encodeLen * 8;
  uint32_t bucketBitMax = (bucketsLog2 > 0) ? bucketsLog2 : 1;
  uint32_t bucketBitPos = 0;
  uint32_t bucketU32 = 0;
  uint32_t btemp = 0;
  uint32_t subStep = bitMax / bucketBitMax;
  subStep = (subStep >= 1) ? subStep : 1;
  uint32_t subCountOneWaterMark = subStep >> 1;
  uint32_t oneCnt = 0;
  uint32_t nextCheckPoint = subStep;
  uint32_t btempSampled = 0;
  for (size_t i = 0; i < bitMax; i++) {
    btemp = 0;
    if (rawFloat[i] > 0) {
      size_t byteIdx = i >> 3;
      size_t bitIdx = i & 0x07;
      ru[byteIdx] |= (1 << bitIdx);
      btemp = 1;
    }
    oneCnt += btemp;
    // process the bucket id for each bit
    if (i == nextCheckPoint) {
      if (oneCnt > subCountOneWaterMark) {
        btempSampled = 1;
      } else {
        btempSampled = 0;
      }
      oneCnt = 0;
      if (bucketBitPos == bucketBitMax - 2) {
        subCountOneWaterMark = (bitMax - nextCheckPoint) >> 1;
        nextCheckPoint = bitMax - 1;
      } else {
        nextCheckPoint += subStep;
      }
      if (bucketBitPos < bucketBitMax) {
        bucketU32 |= (btempSampled << bucketBitPos);
        bucketBitPos++;
      }
    }

  }
  if (numberOfBuckets == 1) {
    bktRu = 0;
  } else {
    bktRu = bucketU32 % numberOfBuckets;
  }
  return bktRu;
}
std::vector<uint64_t> CANDY::BucketedFlatIndex::encodeMultiRows(torch::Tensor &tensor) {
  size_t encodeLines = (size_t) tensor.size(0);
  std::vector<uint64_t> ru(encodeLines, 0);
  if (bucketModeNumber == 0) {
    /**
     * @brief mean
     */
    for (size_t i = 0; i < encodeLines; i++) {
      auto rowI = tensor.slice(0, i, i + 1);
      ru[i] = encodeSingleRowMean(rowI);
    }
  } else if (bucketModeNumber == 2) {
    auto tensorEncode = myMLModel->hash(tensor);
    for (size_t i = 0; i < encodeLines; i++) {
      float fru = tensorEncode[i].item<float>() * numberOfBuckets;
      if (fru > 0 && fru < (numberOfBuckets)) {
        ru[i] = (uint64_t) fru;
      }
    }
  } else {
    /**
    * @brief lsh
    */
    torch::Tensor lshResult = torch::matmul(tensor, rotationMatrix);
    for (size_t i = 0; i < encodeLines; i++) {
      auto rowI = lshResult.slice(0, i, i + 1);
      ru[i] = encodeSingleRowLsh(rowI);
    }
  }
  return ru;
}
void CANDY::BucketedFlatIndex::reset() {
  //lastNNZ = -1;
  for (size_t i = 0; i < (size_t) numberOfBuckets; i++) {
    buckets[i]->reset();
  }
}
bool CANDY::BucketedFlatIndex::insertTensor(torch::Tensor &t) {
  if (numberOfBuckets == 1) {
    return buckets[0]->insertTensor(t);
  }
  auto bktIdx = encodeMultiRows(t);
  size_t encodeLines = (size_t) t.size(0);
  for (size_t i = 0; i < encodeLines; i++) {
    auto rowI = t.slice(0, i, i + 1);
    buckets[bktIdx[i]]->insertTensor(rowI);
  }
  return true;
}

bool CANDY::BucketedFlatIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  if (numberOfBuckets == 1) {
    return buckets[0]->deleteTensor(t, k);
  }
  auto bktIdx = encodeMultiRows(t);
  size_t encodeLines = (size_t) t.size(0);
  for (size_t i = 0; i < encodeLines; i++) {
    auto rowI = t.slice(0, i, i + 1);
    buckets[bktIdx[i]]->deleteTensor(t, k);
  }
  return true;
}

bool CANDY::BucketedFlatIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  if (numberOfBuckets == 1) {
    return buckets[0]->reviseTensor(t, w);
  }
  auto bktIdx = encodeMultiRows(t);
  size_t encodeLines = (size_t) t.size(0);
  for (size_t i = 0; i < encodeLines; i++) {
    auto rowI = t.slice(0, i, i + 1);
    auto rowIW = w.slice(0, i, i + 1);
    buckets[bktIdx[i]]->reviseTensor(rowI, rowIW);
  }
  return true;
}
torch::Tensor CANDY::BucketedFlatIndex::searchSingleRow(torch::Tensor &q, uint64_t bktIdx, int64_t k) {
  int64_t minimumNum = k;
  size_t bkts = numberOfBuckets;
  if (bktIdx > bkts) { return torch::zeros({minimumNum, q.size(1)}); }
  /**
   * @brief 1. test whether the buckets[idx] has enough tensors,
   */
  if (buckets[bktIdx]->size() >= minimumNum) {
    INTELLI_INFO("Bucket " + to_string(bktIdx) + " , has" + to_string(buckets[bktIdx]->size()) + "candidates");
    return buckets[bktIdx]->searchTensor(q, k)[0];
  }
  INTELLI_WARNING("Warning, need to expand the search");
  size_t testTensors = 0;
  /**
  * @brief 2. if not, try to expand
  */
  uint64_t leftMostExpand = bktIdx;
  uint64_t rightMostExpand = bkts - 1 - bktIdx;
  uint64_t leftExpand = (bktIdx == 0) ? 0 : 1;
  uint64_t rightExpand = (bktIdx == (bkts - 1)) ? 0 : 1;
  bool reachedLeftMost = (bktIdx == 0);
  bool reachedRightMost = (bktIdx == (bkts - 1));
  testTensors += buckets[bktIdx]->size();
  torch::Tensor dbTensor = torch::zeros({(int64_t) minimumNum, q.size(1)});
  int64_t lastNNZ = -1;
  if (testTensors > 0) {
    auto getTensor = buckets[bktIdx]->rawData();
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &getTensor, &lastNNZ);
    // //std::cout<<"append\n"<<getTensor<<std::endl;
  }
  while (testTensors < (uint64_t) minimumNum
      && ((reachedRightMost && reachedLeftMost) == false)) { // //std::cout<<"enter while"<<std::endl;
    if ((!reachedLeftMost)) {
      auto getSize = buckets[bktIdx - leftExpand]->size();
      //  //std::cout<<"try bucket (left)"<<bktIdx-leftExpand<<"size "<<getSize<<std::endl;
      if (getSize > 0) {
        auto getTensor = buckets[bktIdx - leftExpand]->rawData();
        INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &getTensor, &lastNNZ);
        testTensors += getTensor.size(0);
        // //std::cout<<"append LEFT\n"<<getTensor<<std::endl;
      }

      leftExpand++;
      if (leftExpand > leftMostExpand) {
        reachedLeftMost = true;
        leftExpand = leftMostExpand;
      }
    }
    if (!reachedRightMost) {
      auto getSize = buckets[bktIdx + rightExpand]->size();
      //  //std::cout<<"try bucket (right)"<<bktIdx+rightExpand<<"size "<<getSize<<std::endl;
      if (getSize > 0) {
        auto getTensor = buckets[bktIdx + rightExpand]->rawData();
        INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &getTensor, &lastNNZ);
        testTensors += getTensor.size(0);
        // //std::cout<<"append right\n"<<getTensor<<std::endl;
      }
      rightExpand++;
      if (rightExpand > rightMostExpand) {
        reachedRightMost = true;
        rightExpand = rightMostExpand;
      }
    }
  }
  /**
   * @brief search on the expanded dbTensor
   */
  faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
  torch::Tensor ru = torch::zeros({k, q.size(1)});
  auto queryTensor = q;
  float *dbData = dbTensor.data_ptr<float>();
  float *queryData = queryTensor.contiguous().data_ptr<float>();
  indexFlat.add(dbTensor.size(0), dbData); // add vectors to the index
  int64_t querySize = 1;
  std::vector<faiss::idx_t> idxRu(k * querySize);
  std::vector<float> distance(k * querySize);
  indexFlat.search(querySize, queryData, k, distance.data(), idxRu.data());
  for (int64_t j = 0; j < k; j++) {
    int64_t tempIdx = idxRu[j];
    if (tempIdx >= 0) { ru.slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1); }
  }
  return ru;
}

std::vector<torch::Tensor> CANDY::BucketedFlatIndex::searchTensor(torch::Tensor &q, int64_t k) {

  if (numberOfBuckets == 1) {
    return buckets[0]->searchTensor(q, k);
  }
  size_t queryLen = q.size(0);
  std::vector<torch::Tensor> ru(queryLen);
  auto bktIdx = encodeMultiRows(q);
  for (size_t i = 0; i < queryLen; i++) {
    auto rowI = q.slice(0, i, i + 1);
    ru[i] = searchSingleRow(rowI, bktIdx[i], k);
  }
  return ru;
}
bool CANDY::BucketedFlatIndex::loadInitialTensor(torch::Tensor &t) {
  if (bucketModeNumber != 2) {
    return insertTensor(t);
  }
  torch::Tensor A = t; // Placeholder for your tensor

  // Parameters
  int64_t num_samples = t.size(0) / 2; // Number of samples to select for x1 and x2
  if (buildingSamples > 0) {
    num_samples = buildingSamples;
  }
  int64_t k = buildingANNK; // Number of nearest neighbors to consider

  // Randomly select indices for x1 and x2
  std::vector<int> indices(A.size(0));
  std::iota(indices.begin(), indices.end(), 0);
  std::random_shuffle(indices.begin(), indices.end());

  // Split A into x1 and x2 based on selected indices
  torch::Tensor
      x1 = A.index_select(0, torch::tensor(std::vector<int64_t>(indices.begin(), indices.begin() + num_samples)));
  torch::Tensor x2 = A.index_select(0,
                                    torch::tensor(std::vector<int64_t>(indices.begin() + num_samples,
                                                                       indices.begin() + 2 * num_samples)));

  // Convert x1 to a format suitable for Faiss
  // Note: Faiss expects data in a flat, contiguous array format (float)
  x1 = x1.contiguous().to(torch::kFloat32);
  float *x1_data = x1.data_ptr<float>();

  // Create a Faiss index for A
  faiss::IndexFlat index(vecDim, faissMetric); // call constructor
  index.add(A.size(0), A.data_ptr<float>()); // Adding the dataset to the index

  // Allocate arrays for Faiss results
  std::vector<float> distances(num_samples * k);
  std::vector<faiss::idx_t> labels(num_samples * k);

  // Perform the search for x1 in A
  index.search(num_samples, x1_data, k, distances.data(), labels.data());

  // Generate labels based on whether x2's index appears in x1's K-nearest neighbors
  std::vector<int64_t> similarity_labels(num_samples, 0);
  for (size_t i = 0; i < num_samples; ++i) {
    for (size_t j = 0; j < k; ++j) {
      if (labels[i * k + j] == indices[num_samples + i]) {
        similarity_labels[i] = 1;
        break;
      }
    }
  }
  INTELLI_INFO("Labeling data is done");
  // Convert the std::vector<int64_t> to a torch::Tensor
  torch::Tensor labels_tensor = torch::tensor(similarity_labels, torch::dtype(torch::kInt64));
  myMLModel->trainModel(x1, x2, labels_tensor);
  insertTensor(t);
  return true;
}
