/*! \file OnlineIVFL2HIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <OnlineIVFL2HIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
static uint32_t L2HnnzBits(uint32_t a) {
  if (a == 0) {
    return 1;
  }
  return 32 - __builtin_clz(a);
}
torch::Tensor CANDY::OnlineIVFL2HIndex::randomProjection(torch::Tensor &a) {
  return myMLModel->hash(a);
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

#ifndef ONLINEIVFL2H_NEXT_POW_2
/**
 *  compute the next number, greater than or equal to 32-bit unsigned v.
 *  taken from "bit twiddling hacks":
 *  http://graphics.stanford.edu/~seander/bithacks.html
 */
#define ONLINEIVFL2H_NEXT_POW_2(V)                           \
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

bool CANDY::OnlineIVFL2HIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  vecDim = cfg->tryI64("vecDim", 768, true);
  //expandStep = cfg->tryI64("expandStep", 100, true);
  numberOfBuckets = cfg->tryI64("numberOfBuckets", 1, true);
  encodeLen = cfg->tryI64("encodeLen", 1, true);
  candidateTimes = cfg->tryI64("candidateTimes", 1, true);

  buildingSamples = cfg->tryI64("buildingSamples", cfg->tryI64("sampleRows", 2048, true), true);
  buildingANNK = cfg->tryI64("buildingANNK", 10, true);
  positiveSampleRatio = cfg->tryDouble("positiveSampleRatio", 0.1, true);
  if (positiveSampleRatio > 1 || positiveSampleRatio < 0) {
    positiveSampleRatio = 0.1;
  }
  if (numberOfBuckets < 0) {
    numberOfBuckets = 1;
  }

  if (numberOfBuckets > 1) {
    size_t bks = numberOfBuckets;
    ONLINEIVFL2H_NEXT_POW_2(bks);
    numberOfBuckets = bks;
    INTELLI_INFO("Note, adjust the number of buckets into" + std::to_string(numberOfBuckets));
    uint32_t tb = numberOfBuckets;
    bucketsLog2 = L2HnnzBits(tb);
  }
  INTELLI_INFO("#IVFL2H, #Buckets=" + std::to_string(numberOfBuckets) + ",encode length=" + std::to_string(encodeLen)
                   + ", reference value point=" + std::to_string(maskReference) + "sampling "
                   + std::to_string(bucketsLog2) + " bits at first tier");
  //creat the buckets
  IVFList.init(numberOfBuckets, encodeLen);
  /**
   ** @brief generate the rotation matrix for random projection
   */
  torch::manual_seed(114514);
  myMLModel = newMLPHashingModel();
  myMLModel->init(vecDim, encodeLen * 8, cfg);
  torch::Tensor a_real = torch::randn({vecDim, vecDim});
  return true;
}
void CANDY::OnlineIVFL2HIndex::trainModelWithData(torch::Tensor &t) {
  torch::Tensor A = t; // Placeholder for your tensor

  // Parameters
  int64_t num_samples = t.size(0) / 2; // Number of samples to select for x1 and x2
  if (buildingSamples > 0 && buildingSamples < t.size(0) / 2) {
    num_samples = buildingSamples;
  }
  int64_t k = buildingANNK; // Number of nearest neighbors to consider

  // Randomly select indices for x1 and x2


  // Split A into x1 and x2 based on selected indices
  torch::Tensor
      x1 = INTELLI::IntelliTensorOP::rowSampling(A, num_samples);

  // Convert x1 to a format suitable for Faiss
  // Note: Faiss expects data in a flat, contiguous array format (float)
  x1 = x1.contiguous().to(torch::kFloat32);
  float *x1_data = x1.data_ptr<float>();

  // Create a Faiss index for A
  faiss::IndexFlat index(vecDim, faissMetric); // call constructor
  index.add(A.size(0), A.contiguous().data_ptr<float>()); // Adding the dataset to the index

  // Allocate arrays for Faiss results
  std::vector<float> distances(num_samples * k);
  std::vector<float> distances2(num_samples * k * 2);
  std::vector<faiss::idx_t> labels(num_samples * k);
  std::vector<faiss::idx_t> labels2(num_samples * k * 2);
  // Perform the search for x1 in A
  index.search(num_samples, x1_data, k, distances.data(), labels.data());
  index.search(num_samples, x1_data, k * 2, distances2.data(), labels2.data());
  auto x1Temp = x1.clone();
  torch::manual_seed(999);
  // Example tensor
  torch::Tensor randTable = torch::rand({num_samples * k}); // A tensor with 10 elements
  /***
   * @brief place xiTemp as x1;x1;...(k x1 in total)
   */
  for (int64_t i = 1; i < k; i++) {
    INTELLI::IntelliTensorOP::appendRows(&x1Temp, &x1);
  }
  auto x2Temp = torch::zeros(x1Temp.sizes());
  // Generate labels based on whether x2's index appears in x1's K-nearest neighbors
  std::vector<int64_t> similarity_labels(x1Temp.size(0), 0);
  /***
   *
  // Perform the search for x1 in A
  index.search(num_samples, x1_data, k, distances.data(), labels.data());

  // Generate labels based on whether x2's index appears in x1's K-nearest neighbors
  std::vector<int64_t> similarity_labels(num_samples, 0);
  for (int64_t i = 0; i < num_samples; ++i) {
    for (int64_t j = 0; j < k; ++j) {
      if (labels[i * k + j] == indices[num_samples + i]) {
        similarity_labels[i] = 1;
        break;
      }
    }
  }
   */
  int64_t positiveCnt = 0;
  for (int64_t i = 0; i < num_samples; ++i) {
    for (int64_t j = 0; j < k; ++j) {
      int64_t idx = labels[i * k + j];
      if (randTable[j * num_samples + i].item<float>() < positiveSampleRatio) {
        idx = labels[i * k + j];
        similarity_labels[j * num_samples + i] = 1;
        positiveCnt++;
      } else {
        idx = labels2[i * 2 * k + j + k];
        similarity_labels[j * num_samples + i] = 0;
      }
      x2Temp.slice(0, j * num_samples + i, j * num_samples + i + 1) = t.slice(0, idx, idx + 1);
    }
  }
  INTELLI_INFO("Labeling data is done, " + to_string(positiveCnt) + " positive.");
  // Convert the std::vector<int64_t> to a torch::Tensor
  torch::Tensor labels_tensor = torch::tensor(similarity_labels, torch::dtype(torch::kInt64));
  myMLModel->trainModel(x1Temp, x2Temp, labels_tensor);
}
bool CANDY::OnlineIVFL2HIndex::loadInitialTensor(torch::Tensor &t) {
  trainModelWithData(t);
  insertTensor(t);
  return true;
}
bool CANDY::OnlineIVFL2HIndex::loadInitialTensorAndQueryDistribution(torch::Tensor &t, torch::Tensor &query) {
  auto qTemp = query.clone();
  INTELLI::IntelliTensorOP::appendRows(&qTemp, &t);
  trainModelWithData(qTemp);
  /*faiss::IndexFlat index(vecDim, faissMetric); // call constructor
  index.add(t.size(0), t.contiguous().data_ptr<float>());
  INTELLI_INFO("Load distribution of Query, size ="+ to_string(query.size(0)));
  // Parameters

  int64_t k = buildingANNK; // Number of nearest neighbors to consider

  // Allocate arrays for Faiss results
  std::vector<float> distances(query.size(0) * k);
  std::vector<faiss::idx_t> labels(query.size(0) * k);
  // Perform the search for x1 in A
  index.search(query.size(0), query.contiguous().data_ptr<float>(), k, distances.data(), labels.data());
   auto x1=query.clone();
  auto x2=torch::zeros({query.size(0)*k*2,query.size(1)});

  // Generate labels based on whether x2's index appears in x1's K-nearest neighbors
  std::vector<int64_t> similarity_labels(query.size(0)*k*2, 0);
  int64_t lastNNZ=-1;
  for (; x1.size(0) < query.size(0)*k*2;) {
    INTELLI::IntelliTensorOP::appendRows(&x1, &query);
  }
  int64_t labelPos=0;

  for (int64_t i=0;i< query.size(0);i++) {
    for (int64_t j=0;j<k;j++) {
      int64_t positiveIdx=labels[i * k + j];
      auto tj=t.slice(0,positiveIdx,positiveIdx+1);
      INTELLI::IntelliTensorOP::appendRowsBufferMode(&x2,&tj,&lastNNZ);
      similarity_labels[labelPos]=1;
      labelPos++;
    }
  }

  for (int64_t i=0;i< query.size(0);i++) {
    for (int64_t j=0;j<k;j++) {
      int64_t negativeIdx=t.size(0)-labels[i * k + j];
      auto tnj=t.slice(0,negativeIdx,negativeIdx+1);
      INTELLI::IntelliTensorOP::appendRowsBufferMode(&x2,&tnj,&lastNNZ);
      similarity_labels[labelPos]=0;
      labelPos++;
    }
  }

  torch::Tensor labels_tensor = torch::tensor(similarity_labels, torch::dtype(torch::kInt64));
  INTELLI_INFO("start fine tune");
  myMLModel->trainModel(x1, x2, labels_tensor);*/
  insertTensor(t);
  return true;
}
