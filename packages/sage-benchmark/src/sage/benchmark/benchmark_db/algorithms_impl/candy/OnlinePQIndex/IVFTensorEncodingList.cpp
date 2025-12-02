#include <OnlinePQIndex/IVFTensorEncodingList.h>
#include <Utils/IntelliLog.h>
#include <algorithm>
void CANDY::IVFListCell::insertTensorPtr(INTELLI::TensorPtr tp) {
  tl.push_back(tp);
  tensors++;
}
void CANDY::IVFListCell::insertTensor(torch::Tensor &t) {
  insertTensorPtr(newTensor(t));
}

static std::string encodeToString(std::vector<uint8_t> &encode) {
  std::string str;
  for (size_t i = 0; i < encode.size(); i++) {
    str += std::to_string((int) encode[i]);
    str += "-";
  }
  return str;
}
bool CANDY::IVFListCell::deleteTensorPtr(INTELLI::TensorPtr tp) {
  for (auto ele = tl.begin(); ele != tl.end(); ++ele) {
    if (*ele == tp) {
      tl.erase(ele);
      tensors--;
      return true;
    }
  }
  return false;
}

bool CANDY::IVFListCell::deleteTensor(torch::Tensor &t) {
  for (auto ele = tl.begin(); ele != tl.end(); ++ele) {
    auto tp = *ele;
    if (torch::equal(*tp, t)) {
      tl.erase(ele);
      tensors--;
      return true;
    }
  }
  return false;
}
torch::Tensor CANDY::IVFListCell::getAllTensors(void) {
  if (tensors == 0) {
    return torch::zeros({1, 1});
  }
  auto startRow = *tl.begin();
  auto cols = startRow->size(1);
  torch::Tensor ru = torch::zeros({tensors, cols});
  int64_t lastNNZ = -1;
  for (auto ele = tl.begin(); ele != tl.end(); ++ele) {
    auto tp = *ele;
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, tp.get(), &lastNNZ);
  }
  return ru;
}
void CANDY::IVFListBucket::insertTensorWithEncode(torch::Tensor &t, std::vector<uint8_t> &encode, bool isConcurrent) {
  if (isConcurrent) {
    lock();
    tensors++;
    unlock();
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      if (celPtr->getEncode() == encode) {
        celPtr->lock();
        celPtr->insertTensor(t);
        celPtr->unlock();
        return;
      }
    }
    IVFListCellPtr cellNew = newIVFListCell();
    cellNew->setEncode(encode);
    cellNew->insertTensor(t);
    cellPtrs.push_back(cellNew);
    return;
  } else {
    tensors++;
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      if (celPtr->getEncode() == encode) {
        celPtr->insertTensor(t);
        return;
      }
    }
    IVFListCellPtr cellNew = newIVFListCell();
    cellNew->setEncode(encode);
    cellNew->insertTensor(t);
    cellPtrs.push_back(cellNew);
    return;
  }
}

bool CANDY::IVFListBucket::deleteTensorWithEncode(torch::Tensor &t, std::vector<uint8_t> &encode, bool isConcurrent) {
  bool probeDeletion;
  if (isConcurrent) {
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      if (celPtr->getEncode() == encode) {
        celPtr->lock();
        probeDeletion = celPtr->deleteTensor(t);
        celPtr->unlock();
        if (probeDeletion) {

          lock();
          tensors--;
          if (celPtr->size() == 0) {
            cellPtrs.erase(ele);
          }
          unlock();
          return true;
        }

      }
    }
    return false;
  } else {
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      if (celPtr->getEncode() == encode) {
        probeDeletion = celPtr->deleteTensor(t);
        if (probeDeletion) {
          tensors--;
          if (celPtr->size() == 0) {
            cellPtrs.erase(ele);
          }
          return true;
        }

      }
    }
    return false;
  }
}

bool CANDY::IVFListBucket::deleteTensor(torch::Tensor &t, bool isConcurrent) {
  bool probeDeletion;
  if (isConcurrent) {
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      celPtr->lock();
      probeDeletion = celPtr->deleteTensor(t);
      celPtr->unlock();
      if (probeDeletion) {
        lock();
        tensors--;
        unlock();
        return true;
      }
    }
    return false;
  } else {
    for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
      auto celPtr = *ele;
      probeDeletion = celPtr->deleteTensor(t);
      if (probeDeletion) {
        tensors--;
        return true;
      }
    }
    return false;
  }
}
torch::Tensor CANDY::IVFListBucket::getAllTensors() {
  if (tensors == 0) {
    torch::Tensor emptyRu;
    return emptyRu;
  }
  auto firstCell = *cellPtrs.begin();
  auto cols = firstCell->getAllTensors().size(1);
  torch::Tensor ru = torch::zeros({tensors, cols});
  int64_t lastNNZ = -1;
  for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
    auto t = (*ele)->getAllTensors();
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &t, &lastNNZ);
  }
  return ru;
}
torch::Tensor CANDY::IVFListBucket::getAllTensorsWithEncode(std::vector<uint8_t> &_encode) {
  for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
    if ((*ele)->getEncode() == _encode) { return (*ele)->getAllTensors(); }
  }
  torch::Tensor emptyRu;
  return emptyRu;
}
static uint64_t hammingDistance(const std::vector<uint8_t> &a, const std::vector<uint8_t> &b) {
  // Check if vectors have the same length
  if (a.size() != b.size()) {
    std::cerr << "Error: Vectors must have the same length." << std::endl;
    return -1;  // Return an error code
  }
  uint64_t distance = 0;
  // Iterate over elements and count differences
  for (size_t i = 0; i < a.size(); ++i) {
    // Assuming elements are uint8_t (8-bit unsigned integers)
    uint8_t xorResult = a[i] ^ b[i];
    // Count set bits in the XOR result using __builtin_clz
    while (xorResult) {
      distance += 8 - __builtin_clz(xorResult);
      xorResult <<= 8 - __builtin_clz(xorResult);
    }
  }

  return distance;
}
static std::vector<size_t> argsort(const std::vector<uint64_t> &vec) {
  // Initialize an index vector with the same size as the input vector
  std::vector<size_t> indices(vec.size());
  std::iota(indices.begin(), indices.end(), 0);  // Fill with 0, 1, 2, ...

  // Sort indices based on the values in the vector
  std::sort(indices.begin(), indices.end(), [&vec](size_t i, size_t j) {
    return vec[i] < vec[j];
  });

  return indices;
}

torch::Tensor CANDY::IVFListBucket::getMinimumTensorsUnderHamming(std::vector<uint8_t> &encode,
                                                                  int64_t minNumber,
                                                                  int64_t vecDim) {
  torch::Tensor ru = torch::zeros({(int64_t) minNumber, vecDim});
  int64_t lastNNZ = -1;
  int64_t testSize = 0;
  int64_t enoughNumber = (minNumber > tensors) ? tensors : minNumber;
  /**
   * @brief 1. try exact match
   */
  auto exactMatch = getAllTensorsWithEncode(encode);
  testSize += exactMatch.size(0);
  if (testSize >= enoughNumber) {
    return exactMatch;
  }
  if (testSize > 0) {
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &exactMatch, &lastNNZ);
  }
  /**
  * @brief 2. scan
  */
  size_t encodingsCnt = cellPtrs.size();
  std::vector<IVFListCellPtr> cellVec(encodingsCnt);
  std::vector<uint64_t> hammingDistanceVec(encodingsCnt);
  size_t i = 0;
  for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
    cellVec[i] = (*ele);
    auto eleEncode = (*ele)->getEncode();
    hammingDistanceVec[i] = hammingDistance(eleEncode, encode);
    i++;
  }
  /**
   * @brief 3. sort
   */
  auto sortedIdx = argsort(hammingDistanceVec);
  for (size_t i = 0; i < sortedIdx.size(); i++) {
    auto matchi = cellVec[i]->getAllTensors();
    if (matchi.size(0) > 0) {
      testSize += matchi.size(0);
      INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &matchi, &lastNNZ);
    }
    if (testSize >= enoughNumber) {
      return ru;
    }
  }
  return ru;
}
int64_t CANDY::IVFListBucket::sizeWithEncode(std::vector<uint8_t> &_encode) {
  for (auto ele = cellPtrs.begin(); ele != cellPtrs.end(); ++ele) {
    if ((*ele)->getEncode() == _encode) {
      return (*ele)->size();

    }
  }
  return 0;
}
void CANDY::IVFTensorEncodingList::init(size_t bkts, size_t _encodeLen) {
  bucketPtrs = std::vector<IVFListBucketPtr>(bkts);
  for (size_t i = 0; i < bkts; i++) {
    bucketPtrs[i] = newIVFListBucket();
  }
  encodeLen = _encodeLen;
}
void CANDY::IVFTensorEncodingList::insertTensorWithEncode(torch::Tensor &t,
                                                          std::vector<uint8_t> &encode,
                                                          uint64_t bktIdx,
                                                          bool isConcurrent) {
  size_t bkts = bucketPtrs.size();
  if (bktIdx >= bkts) { return; }
  bucketPtrs[bktIdx]->insertTensorWithEncode(t, encode, isConcurrent);

}
bool CANDY::IVFTensorEncodingList::deleteTensorWithEncode(torch::Tensor &t,
                                                          std::vector<uint8_t> &encode,
                                                          uint64_t bktIdx,
                                                          bool isConcurrent) {
  size_t bkts = bucketPtrs.size();
  if (bktIdx >= bkts) { return false; }
  bool bktProbe = bucketPtrs[bktIdx]->deleteTensorWithEncode(t, encode, isConcurrent);
  if (!bktProbe) {
    return false;
  }
  return true;
}
torch::Tensor CANDY::IVFTensorEncodingList::getMinimumNumOfTensors(torch::Tensor &t,
                                                                   std::vector<uint8_t> &encode,
                                                                   uint64_t bktIdx,
                                                                   int64_t minimumNum) {
  size_t testTensors = 0;
  size_t bkts = bucketPtrs.size();
  if (bktIdx > bkts) { return torch::zeros({minimumNum, t.size(1)}); }
  /**
   * @brief 1. test whether the buckt[idx] has enough tensors,
   */
  /*INTELLI_INFO(
      std::to_string(bktIdx) + ",code=" + encodeToString(encode) + " has " + std::to_string(bucketPtrs[bktIdx]->size())
          + " candidates");*/
  if (bucketPtrs[bktIdx]->size() >= minimumNum) {
    return getMinimumNumOfTensorsInsideBucket(t, encode, bktIdx, minimumNum);
  }
  /**
  * @brief 2. if not, try to expand
  */
  uint64_t leftMostExpand = bktIdx;
  uint64_t rightMostExpand = bkts - 1 - bktIdx;
  uint64_t leftExpand = (bktIdx == 0) ? 0 : 1;
  uint64_t rightExpand = (bktIdx == (bkts - 1)) ? 0 : 1;
  bool reachedLeftMost = (bktIdx == 0);
  bool reachedRightMost = (bktIdx == (bkts - 1));
  testTensors += bucketPtrs[bktIdx]->size();
  torch::Tensor ru = torch::zeros({(int64_t) minimumNum, t.size(1)});
  int64_t lastNNZ = -1;
  if (testTensors > 0) {
    auto getTensor = bucketPtrs[bktIdx]->getAllTensors();
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
    // //std::cout<<"append\n"<<getTensor<<std::endl;
  }
  //std::cout<<reachedLeftMost<<reachedRightMost<<std::endl;

  while (testTensors < (uint64_t) minimumNum
      && ((reachedRightMost && reachedLeftMost) == false)) { // //std::cout<<"enter while"<<std::endl;
    if ((!reachedLeftMost)) {
      auto getSize = bucketPtrs[bktIdx - leftExpand]->size();
      testTensors += getSize;
      //  //std::cout<<"try bucket (left)"<<bktIdx-leftExpand<<"size "<<getSize<<std::endl;
      if (getSize > 0) {
        auto getTensor = bucketPtrs[bktIdx - leftExpand]->getAllTensors();
        INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
        // //std::cout<<"append LEFT\n"<<getTensor<<std::endl;
      }

      leftExpand++;
      if (leftExpand > leftMostExpand) {
        reachedLeftMost = true;
        leftExpand = leftMostExpand;
      }
    }
    if (!reachedRightMost) {
      auto getSize = bucketPtrs[bktIdx + rightExpand]->size();
      testTensors += getSize;
      //  //std::cout<<"try bucket (right)"<<bktIdx+rightExpand<<"size "<<getSize<<std::endl;
      if (getSize > 0) {
        auto getTensor = bucketPtrs[bktIdx + rightExpand]->getAllTensors();
        INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
        // //std::cout<<"append right\n"<<getTensor<<std::endl;
      }
      rightExpand++;
      if (rightExpand > rightMostExpand) {
        reachedRightMost = true;
        rightExpand = rightMostExpand;
      }
    }
  }
  return ru;
}

torch::Tensor CANDY::IVFTensorEncodingList::getMinimumNumOfTensorsHamming(torch::Tensor &t,
                                                                          std::vector<uint8_t> &encode,
                                                                          uint64_t bktIdx,
                                                                          int64_t minimumNum) {
  size_t testTensors = 0;
  size_t bkts = bucketPtrs.size();
  if (bktIdx > bkts) { return torch::zeros({minimumNum, t.size(1)}); }
  /*INTELLI_INFO(
      std::to_string(bktIdx) + ",code=" + encodeToString(encode) + " has " + std::to_string(bucketPtrs[bktIdx]->size())
          + " candidates");*/
  /**
   * @brief 1. test whether the buckt[idx] has enough tensors,
   */
  if (bucketPtrs[bktIdx]->size() >= minimumNum) {

    return getMinimumNumOfTensorsInsideBucketHamming(t, encode, bktIdx, minimumNum);
  }
  /**
  * @brief 2. if not, try to expand
  */
  uint64_t leftMostExpand = bktIdx;
  uint64_t rightMostExpand = bkts - 1 - bktIdx;
  uint64_t leftExpand = (bktIdx == 0) ? 0 : 1;
  uint64_t rightExpand = (bktIdx == (bkts - 1)) ? 0 : 1;
  bool reachedLeftMost = (bktIdx == 0);
  bool reachedRightMost = (bktIdx == (bkts - 1));
  testTensors += bucketPtrs[bktIdx]->size();
  torch::Tensor ru = torch::zeros({(int64_t) minimumNum, t.size(1)});
  int64_t lastNNZ = -1;
  if (testTensors > 0) {
    auto getTensor = bucketPtrs[bktIdx]->getAllTensors();
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
    // //std::cout<<"append\n"<<getTensor<<std::endl;
  }
  //std::cout<<reachedLeftMost<<reachedRightMost<<std::endl;

  while (testTensors < (uint64_t) minimumNum
      && ((reachedRightMost && reachedLeftMost) == false)) { // //std::cout<<"enter while"<<std::endl;
    if ((!reachedLeftMost)) {
      auto getSize = bucketPtrs[bktIdx - leftExpand]->size();
      //  //std::cout<<"try bucket (left)"<<bktIdx-leftExpand<<"size "<<getSize<<std::endl;
      if (getSize > 0) {
        auto getTensor = getMinimumNumOfTensorsInsideBucketHamming(t, encode, bktIdx - leftExpand, minimumNum);
        INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
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
      auto getSize = bucketPtrs[bktIdx + rightExpand]->size();
      //  //std::cout<<"try bucket (right)"<<bktIdx+rightExpand<<"size "<<getSize<<std::endl;
      if (getSize > 0) {
        auto getTensor = getMinimumNumOfTensorsInsideBucketHamming(t, encode, bktIdx + rightExpand, minimumNum);
        INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
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
  return ru;
}
torch::Tensor CANDY::IVFTensorEncodingList::getMinimumNumOfTensorsInsideBucket(torch::Tensor &t,
                                                                               std::vector<uint8_t> &encode,
                                                                               uint64_t bktIdx,
                                                                               int64_t minimumNum) {
  size_t testTensors = 0;
  size_t bytes = encode.size();
  size_t reachedLeftMostCnt = 0, reachedRightMostCnt = 0;
  std::vector<bool> reachedLeftMost = std::vector<bool>(bytes);
  std::vector<bool> reachedRightMost = std::vector<bool>(bytes);
  for (size_t i = 0; i < bytes; i++) {
    reachedLeftMost[i] = (encode[i] == 0);
    if (reachedLeftMost[i]) {
      reachedLeftMostCnt++;
    }
    reachedRightMost[i] = (encode[i] == 255);
    if (reachedRightMost[i]) {
      reachedRightMostCnt++;
    }
  }
  /**
   * @brief 1. get the exact encode
   */
  auto exactEncodeTensor = bucketPtrs[bktIdx]->getAllTensorsWithEncode(encode);
  if (exactEncodeTensor.size(0) >= minimumNum) {
    return exactEncodeTensor;
  }
  torch::Tensor ru = torch::zeros({(int64_t) minimumNum, t.size(1)});
  int64_t lastNNZ = -1;
  testTensors += exactEncodeTensor.size(0);
  if (exactEncodeTensor.size(0) > 0) {
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &exactEncodeTensor, &lastNNZ);
    //std::cout<<"append\n"<<exactEncodeTensor<<std::endl;
  }
  uint16_t leftExpand = 1;
  uint16_t rightExpand = 1;
  while (testTensors < (uint64_t) minimumNum && (reachedLeftMostCnt + reachedRightMostCnt < 2 * bytes)
      && (leftExpand <= 255)) {
    //std::cout<<"inside, expand up to"<<(int)leftExpand<<std::endl;
    /**
     * @brief probe the i th byte with left and right expand
     */
    for (size_t i = 0; i < bytes; i++) {  /**
     * @brief left
     */
      if (!reachedLeftMost[i]) {
        auto tempEncode = encode;
        bool ri = reachedLeftMost[i];
        tempEncode[i] = getLeftIdxU8(encode[i], leftExpand, &ri);
        reachedLeftMost[i] = ri;
        if (ri == true) {
          reachedLeftMostCnt++;
        }
        auto getTensor = bucketPtrs[bktIdx]->getAllTensorsWithEncode(tempEncode);
        auto getSize = getTensor.size(0);
        testTensors += getSize;
        if (getSize > 0) {
          INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
          //std::cout<<"append left\n"<<getTensor<<std::endl;
        }
        if (testTensors >= (size_t) minimumNum) {
          return ru;
        }
      }
      /**
     * @brief right
     */
      if (!reachedRightMost[i]) {
        auto tempEncode = encode;
        bool li = reachedRightMost[i];
        tempEncode[i] = getRightIdxU8(encode[i], rightExpand, &li);
        reachedRightMost[i] = li;
        if (li == true) {
          reachedRightMostCnt++;
        }
        auto getTensor = bucketPtrs[bktIdx]->getAllTensorsWithEncode(tempEncode);
        auto getSize = getTensor.size(0);
        testTensors += getSize;
        if (getSize > 0) {
          INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &getTensor, &lastNNZ);
          //std::cout<<"append right\n"<<getTensor<<std::endl;
        }
        if (testTensors >= (size_t) minimumNum) {
          return ru;
        }
      }
    }
    leftExpand++;
    rightExpand++;

  }
  if (testTensors < (size_t) minimumNum) {
    auto moreTensor = bucketPtrs[bktIdx]->getAllTensors();
    torch::manual_seed(2);
    // Probability distribution
    int64_t n = moreTensor.size(0);
    torch::Tensor probs = torch::ones(n) / n;  // default: uniform
    // Sample k indices from range 0 to n for given probability distribution
    torch::Tensor indices = torch::multinomial(probs, minimumNum - testTensors, true);
    auto addedTensor = moreTensor.index_select(0, indices);
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&ru, &addedTensor, &lastNNZ);
  }
  return ru;
}

torch::Tensor CANDY::IVFTensorEncodingList::getMinimumNumOfTensorsInsideBucketHamming(torch::Tensor &t,
                                                                                      std::vector<uint8_t> &encode,
                                                                                      uint64_t bktIdx,
                                                                                      int64_t minimumNum) {
  auto vecDim = t.size(1);
  return bucketPtrs[bktIdx]->getMinimumTensorsUnderHamming(encode, minimumNum, vecDim);
}
