/*! \file OnlineIVFLSHIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <OnlineIVFLSHIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
static uint32_t nnzBits(uint32_t a) {
  if (a == 0) {
    return 1;
  }
  return 32 - __builtin_clz(a);
}
#ifndef ONLINEIVF_NEXT_POW_2
/**
 *  compute the next number, greater than or equal to 32-bit unsigned v.
 *  taken from "bit twiddling hacks":
 *  http://graphics.stanford.edu/~seander/bithacks.html
 */
#define ONLINEIVF_NEXT_POW_2(V)                           \
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
void CANDY::OnlineIVFLSHIndex::genCrsIndices() {
  int64_t n = vecDim;
  // Probability distribution
  torch::Tensor probs = torch::ones(n) / n;  // default: uniform
  crsIndices = torch::multinomial(probs, CRSDim, true);
}
torch::Tensor CANDY::OnlineIVFLSHIndex::crsAmm(torch::Tensor &A,
                                               torch::Tensor &B,
                                               torch::Tensor &indices) {

  auto A_sampled = A.index_select(1, indices);
  auto B_sampled = B.index_select(0, indices);
  return torch::matmul(A_sampled, B_sampled);
}
torch::Tensor CANDY::OnlineIVFLSHIndex::randomProjection(torch::Tensor &a) {
  if (useCRS) {
    if (redoCRSIndices) {
      genCrsIndices();
    }
    return CANDY::OnlineIVFLSHIndex::crsAmm(a, rotationMatrix, crsIndices);
  }
  return torch::matmul(a, rotationMatrix);
}
static torch::Tensor genLshMatrix(int64_t N, int64_t D, std::string tag) {
  torch::Tensor ru;
  if (tag == "gaussian") {
    ru = torch::randn({N, D});
  } else {
    ru = torch::rand({N, D}) - 0.5;
  }
  return ru;
}
bool CANDY::OnlineIVFLSHIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  vecDim = cfg->tryI64("vecDim", 768, true);
  //expandStep = cfg->tryI64("expandStep", 100, true);
  numberOfBuckets = cfg->tryI64("numberOfBuckets", 1, true);
  encodeLen = cfg->tryI64("encodeLen", 1, true);
  candidateTimes = cfg->tryI64("candidateTimes", 1, true);
  maskReference = cfg->tryDouble("maskReference", 0.5, true);
  lshMatrixType = cfg->tryString("lshMatrixType", "gaussian", true);

  if (numberOfBuckets < 0) {
    numberOfBuckets = 1;
  }

  if (numberOfBuckets > 1) {
    size_t bks = numberOfBuckets;
    ONLINEIVF_NEXT_POW_2(bks);
    numberOfBuckets = bks;
    INTELLI_INFO("Note, adjust the number of buckets into" + std::to_string(numberOfBuckets));
    uint32_t tb = numberOfBuckets;
    bucketsLog2 = nnzBits(tb);
  }
  INTELLI_INFO("#IVFLSH, #Buckets=" + std::to_string(numberOfBuckets) + ",encode length=" + std::to_string(encodeLen)
                   + ", reference value point=" + std::to_string(maskReference) + "sampling "
                   + std::to_string(bucketsLog2) + " bits at first tier");
  //creat the buckets
  IVFList.init(numberOfBuckets, encodeLen);
  /**
   ** @brief generate the rotation matrix for random projection
   */
  torch::manual_seed(114514);
  rotationMatrix = genLshMatrix(vecDim, encodeLen * 8, lshMatrixType);

  torch::Tensor a_real = torch::randn({vecDim, vecDim});

  useCRS = cfg->tryI64("useCRS", 0, true);
  if (useCRS) {
    CRSDim = cfg->tryI64("CRSDim", vecDim / 10, true);
    redoCRSIndices = cfg->tryI64("redoCRSIndices", 0, true);
    INTELLI_INFO("I will use column row sampling in the LSH's random projection, preserved dimension ="
                     + std::to_string(CRSDim));
    genCrsIndices();
  }
  return true;
}
std::vector<uint8_t> CANDY::OnlineIVFLSHIndex::encodeSingleRow(torch::Tensor &tensor, uint64_t *bucket) {
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
    *bucket = 0;
  } else {
    *bucket = bucketU32 % numberOfBuckets;
  }
  return ru;
}
void CANDY::OnlineIVFLSHIndex::reset() {

}
bool CANDY::OnlineIVFLSHIndex::insertTensor(torch::Tensor &t) {
  int64_t rows = t.size(0);
  auto tr = randomProjection(t);
  for (int64_t i = 0; i < rows; i++) {
    auto rowIR = tr.slice(0, i, i + 1);
    auto rowI = t.slice(0, i, i + 1);
    uint64_t bkt;
    auto rowICode = encodeSingleRow(rowIR, &bkt);
    IVFList.insertTensorWithEncode(rowI, rowICode, (uint64_t) bkt);
  }
  return true;
}
bool CANDY::OnlineIVFLSHIndex::deleteRowsInline(torch::Tensor &t) {
  int64_t rows = t.size(0);
  auto tr = randomProjection(t);
  for (int64_t i = 0; i < rows; i++) {
    auto rowIR = tr.slice(0, i, i + 1);
    auto rowI = t.slice(0, i, i + 1);
    uint64_t bkt;
    auto rowICode = encodeSingleRow(rowIR, &bkt);
    IVFList.deleteTensorWithEncode(rowI, rowICode, (uint64_t) bkt);
  }
  return true;
}

bool CANDY::OnlineIVFLSHIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  if (k == 1) {
    return deleteRowsInline(t);
  }
  auto annsRu = searchTensor(t, k);
  size_t tensors = annsRu.size();
  for (size_t i = 0; i < tensors; i++) {
    deleteRowsInline(annsRu[i]);
  }
  return true;
}

bool CANDY::OnlineIVFLSHIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  deleteTensor(t, 1);
  insertTensor(w);
  return true;
}

std::vector<torch::Tensor> CANDY::OnlineIVFLSHIndex::searchTensor(torch::Tensor &q, int64_t k) {
  int64_t rows = q.size(0);
  std::vector<torch::Tensor> ru((size_t) rows);
  for (int64_t i = 0; i < rows; i++) {
    ru[i] = torch::zeros({k, vecDim});
  }
  auto qr = randomProjection(q);
  //std::cout<<qr<<std::endl;
  //exit(-1);
  //auto qr= randomProjection(q);
  for (int64_t i = 0; i < rows; i++) {
    auto rowIR = qr.slice(0, i, i + 1);
    auto rowI = q.slice(0, i, i + 1);
    uint64_t bkt;
    //exit(-1);
    auto rowICode = encodeSingleRow(rowIR, &bkt);
    auto candidateTensor =
        IVFList.getMinimumNumOfTensorsHamming(rowI, rowICode, (uint64_t) bkt, k * candidateTimes);
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
