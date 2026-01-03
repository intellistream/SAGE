//
// Created by tony on 24-10-21.
//
/*! \file FlatGPUIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <Utils/UtilityFunctions.h>

#include <FlatGPUIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
#include <Utils/IntelliLog.h>
#include <CANDYObject.h>
#include <vector>
#include <algorithm>
#include <utility>
bool CANDY::FlatGPUIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  distanceFunc = distanceIP;
  if (faissMetric != faiss::METRIC_INNER_PRODUCT) {
    INTELLI_WARNING("Switch to L2");
    distanceFunc = distanceL2;
  }
  vecDim = cfg->tryI64("vecDim", 768, true);
  int64_t  vecVolume = cfg->tryI64("vecVolume", 1000, true);
  memBufferSize = cfg->tryI64("memBufferSize", vecVolume+1000, true);
  sketchSize = cfg->tryI64("sketchSize", 10, true);
  DCOBatchSize = cfg->tryI64("DCOBatchSize", memBufferSize, true);
  if (torch::cuda::is_available()) {
    cudaDevice = cfg->tryI64("cudaDevice", -1, true);
    INTELLI_INFO("Cuda is detected. and use this cuda device for DCO:" + std::to_string(cudaDevice));
  }
  if (DCOBatchSize > memBufferSize && memBufferSize > 0) {
    INTELLI_WARNING("DCO batch size is not recommended to exceed mem buffer size.");
    //DCOBatchSize = memBufferSize;
  }
  std::string ammAlgo = cfg->tryString("ammAlgo", "mm", true);
  INTELLI_INFO("Size of DCO=" + std::to_string(DCOBatchSize));
  if (ammAlgo == "crs") {
    ammType = 1;
    INTELLI_INFO("Use crs for amm, sketch size=" + std::to_string(sketchSize));
  } else if (ammAlgo == "smp-pca") {
    ammType = 2;
    INTELLI_INFO("Use smp-pca for amm, sketch size=" + std::to_string(sketchSize));
  } else {
    ammType = 0;
  }
  dmBuffer.init(vecDim, memBufferSize, 0, 0, 0);
  return true;
}
bool CANDY::FlatGPUIndex::startHPC() {

  return true;
}
bool CANDY::FlatGPUIndex::endHPC() {
  //dmBuffer.clear();
  return true;
}
void CANDY::FlatGPUIndex::reset() {

}
bool CANDY::FlatGPUIndex::insertTensor(torch::Tensor &t) {
  if (t.size(0) > memBufferSize && memBufferSize > 0) {
    int64_t total_vectors = t.size(0);
    for (int64_t startPos = 0; startPos < total_vectors; startPos += memBufferSize) {
      int64_t endPos = std::min(startPos + memBufferSize, total_vectors);
      auto tempTensor = t.slice(0, startPos, endPos);
      dmBuffer.appendTensor(tempTensor);
    }
    return true;
  } else {
    return dmBuffer.appendTensor(t);
  }

}

bool CANDY::FlatGPUIndex::deleteTensor(torch::Tensor &t, int64_t k) {

  int64_t rows = t.size(0);
  auto idx = findTopKClosest(t, k, DCOBatchSize);
  std::map<int64_t, int64_t> i64Map;
  for (int64_t i = 0; i < rows * k; i++) {
    if (idx[i] >= 0) {
      if(i64Map.count(idx[i])!=1) {
        dmBuffer.deleteTensor(idx[i], idx[i] + 1);
        i64Map[idx[i]]=1;
      }
     // dmBuffer.deleteTensor(idx[i], idx[i] + 1);
    }
  }
  return true;
}
static
void mergeTopK(std::vector<std::pair<float, int64_t>> &topK,
               const std::vector<std::pair<float, int64_t>> &newResults,
               int64_t top_k) {
  topK.insert(topK.end(), newResults.begin(), newResults.end());
  std::sort(topK.begin(), topK.end(), [](const std::pair<float, int64_t> &a, const std::pair<float, int64_t> &b) {
    return a.first > b.first;
  });
  // Keep only the top_k elements
  if (topK.size() > (size_t) top_k) {
    topK.resize(top_k);
  }
}
static
void mergeTopKVec(std::vector<std::vector<std::pair<float, int64_t>>> &topK,
                  const std::vector<std::vector<std::pair<float, int64_t>>> &newResults,
                  int64_t top_k) {
  size_t rows = topK.size();
  for (size_t i = 0; i < rows; i++) {
    mergeTopK(topK[i], newResults[i], top_k);
  }
}
std::vector<int64_t> CANDY::FlatGPUIndex::findTopKClosest(const torch::Tensor &query,
                                                             int64_t top_k,
                                                             int64_t batch_size
) {
  std::vector<std::vector<std::pair<float, int64_t>>> topK;
  int64_t total_vectors = dmBuffer.size();
  int64_t queryRows = query.size(0);
  //torch::Tensor transposed_query = query.t();
  for (int64_t startPos = 0; startPos < total_vectors; startPos += batch_size) {
    int64_t endPos = std::min(startPos + batch_size, total_vectors);

    // Load batch using getTensor
    torch::Tensor dbBatch = dmBuffer.getTensor(startPos, endPos);
    //std::cout<<"DB data:\n"<<dbBatch<<std::endl;
    // Compute distances
    torch::Tensor distances = distanceFunc(dbBatch, query, cudaDevice, this);
    // torch::matmul(dbBatch, transposed_query);
    //std::cout<<"distance :\n"<<distances.t()<<std::endl;
    auto tStartTopK = std::chrono::high_resolution_clock::now();
    // Use torch::topk to get the top_k smallest distances and their indices
    auto topk_result = torch::topk(distances, top_k, /*dim=*/1, /*largest=*/true, /*sorted=*/true);

    // std::cout<<"top k :\n"<<std::get<0>(topk_result)<<std::endl;
    // Extract top_k distances and indices
    torch::Tensor topk_distances = std::get<0>(topk_result);
    torch::Tensor topk_indices = std::get<1>(topk_result) + startPos;
    gpuComputingUs += chronoElapsedTime(tStartTopK);
    //
    if (cudaDevice > -1 && torch::cuda::is_available()) {
      auto tStart = std::chrono::high_resolution_clock::now();
      topk_distances = topk_distances.to(torch::kCPU);
      topk_indices = topk_indices.to(torch::kCPU);
      gpuCommunicationUs += chronoElapsedTime(tStart);
    }
    // Create a vector of (distance, index) pairs
    std::vector<std::vector<std::pair<float, int64_t>>> batchResults(queryRows);
    for (int64_t i = 0; i < queryRows; i++) {
      for (int64_t j = 0; j < top_k; j++) {
        batchResults[i].emplace_back(topk_distances[i][j].item<float>(), topk_indices[i][j].item<int64_t>());
      }
    }
    // Merge current batch results with topK
    if (topK.empty()) {
      topK = std::move(batchResults);
    } else {
      mergeTopKVec(topK, batchResults, top_k);
    }
  }

  // Extract indices from the topK vector
  std::vector<int64_t> topKIndices(top_k * queryRows);
  for (int64_t i = 0; i < queryRows; i++) {
    for (int64_t j = 0; j < top_k; j++) {
      topKIndices[i * top_k + j] = topK[i][j].second;
    }
  }
  return topKIndices;
}
bool CANDY::FlatGPUIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  if (t.size(0) > w.size(0) || t.size(1) != w.size(1)) {
    return false;
  }
  auto idx = findTopKClosest(t, 1, DCOBatchSize);
  int64_t rows = t.size(0);
  for (int64_t i = 0; i < rows; i++) {
    //auto rowI = t.slice(0, i, i + 1).contiguous();
    if (0 <= idx[i]) {
      auto rowW = w.slice(0, i, i + 1);
      dmBuffer.reviseTensor(idx[i], rowW);
      //INTELLI::IntelliTensorOP::editRows(&dbTensor, &rowW, (int64_t) idx);
    }
  }
  return true;
}
bool CANDY::FlatGPUIndex::resetIndexStatistics() {
  dmBuffer.clearStatistics();
  gpuComputingUs = 0;
  gpuCommunicationUs = 0;
  return true;
}
INTELLI::ConfigMapPtr CANDY::FlatGPUIndex::getIndexStatistics() {
  auto cfg = AbstractIndex::getIndexStatistics();
  cfg->edit("hasExtraStatistics", (int64_t) 1);
  /**
   * @brief count of memory access
   */
  cfg->edit("totalMemReadCnt", (int64_t) dmBuffer.getMemoryReadCntTotal());
  cfg->edit("missMemReadCnt", (int64_t) dmBuffer.getMemoryReadCntMiss());
  double memMissHitRead = dmBuffer.getMemoryReadCntMiss();
  memMissHitRead = memMissHitRead / dmBuffer.getMemoryReadCntTotal();
  cfg->edit("memMissRead", (double) memMissHitRead);
  cfg->edit("totalMemWriteCnt", (int64_t) dmBuffer.getMemoryWriteCntTotal());
  cfg->edit("missMemWriteCnt", (int64_t) dmBuffer.getMemoryWriteCntMiss());
  double memMissHitWrite = dmBuffer.getMemoryWriteCntMiss();
  memMissHitWrite = memMissHitWrite / dmBuffer.getMemoryWriteCntTotal();
  cfg->edit("memMissWrite", (double) memMissHitWrite);
  /**
   * @brief gpu statistics
   */
  if (cudaDevice > -1 && torch::cuda::is_available()) {
    cfg->edit("gpuCommunicationUs", (int64_t) gpuCommunicationUs);
    cfg->edit("gpuComputingUs", (int64_t) gpuComputingUs);
  } else {
    cfg->edit("cpuComputingUs", (int64_t) gpuComputingUs);
  }
  return cfg;
}

std::vector<torch::Tensor> CANDY::FlatGPUIndex::searchTensor(torch::Tensor &q, int64_t k) {
  auto idx = findTopKClosest(q, k, DCOBatchSize);
  //std::cout<<"sorting idx"<<std::endl;

  return getTensorByStdIdx(idx, k);
}

std::vector<torch::Tensor> CANDY::FlatGPUIndex::getTensorByStdIdx(std::vector<int64_t> &idx, int64_t k) {
  int64_t tensors = idx.size() / k;
  std::vector<torch::Tensor> ru(tensors);
  for (int64_t i = 0; i < tensors; i++) {
    ru[i] = torch::zeros({k, vecDim});
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idx[i * k + j];
      if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = dmBuffer.getTensor(tempIdx, tempIdx + 1); }
    }
  }
  return ru;
}
torch::Tensor CANDY::FlatGPUIndex::distanceIP(torch::Tensor db,
                                                 torch::Tensor query,
                                                 int64_t cudaDev,
                                                 FlatGPUIndex *idx) {
  torch::Tensor q0 = query;
  torch::Tensor dbTensor = db;
  int64_t compTime = 0, commTime = 0;
  auto tStart = std::chrono::high_resolution_clock::now();
  if (cudaDev > -1 && torch::cuda::is_available()) {
    // Move tensors to GPU 1
    auto device = torch::Device(torch::kCUDA, cudaDev);
    q0 = q0.to(device);
    dbTensor = dbTensor.to(device);
    commTime = chronoElapsedTime(tStart);
    idx->gpuCommunicationUs += commTime;
  }
  torch::Tensor distances = torch::matmul(dbTensor, q0.t());
  auto ru = distances.t();
  compTime = chronoElapsedTime(tStart) - commTime;
  idx->gpuComputingUs += compTime;
  /*if(cudaDev>-1&&torch::cuda::is_available()){
   ru = ru.to(torch::kCPU);
  }*/
  return ru;
}

torch::Tensor CANDY::FlatGPUIndex::distanceL2(torch::Tensor db0,
                                                 torch::Tensor _q,
                                                 int64_t cudaDev,
                                                 FlatGPUIndex *idx) {
  torch::Tensor dbTensor = db0;
  torch::Tensor query = _q;
  int64_t compTime = 0, commTime = 0;
  auto tStart = std::chrono::high_resolution_clock::now();
  if (cudaDev > -1 && torch::cuda::is_available()) {
    // Move tensors to GPU 1
    auto device = torch::Device(torch::kCUDA, cudaDev);
    dbTensor = dbTensor.to(device);
    query = query.to(device);
    commTime = chronoElapsedTime(tStart);
    idx->gpuCommunicationUs += commTime;
  }
  auto n = dbTensor.size(0);
  auto q = query.size(0);
  auto vecDim = dbTensor.size(1);

  // Ensure result tensor is on the same device as input tensors
  torch::Tensor result = torch::empty({q, n}, dbTensor.options());

  // Compute L2 distance using a for loop
  for (int64_t i = 0; i < q; ++i) {
    auto query_row = query[i].view({1, vecDim}); // [1, vecDim]
    auto diff = dbTensor - query_row; // [n, vecDim]
    auto dist_squared = diff.pow(2).sum(1); // [n]
    result[i] = dist_squared;
  }
  result = -result;
  compTime = chronoElapsedTime(tStart) - commTime;
  idx->gpuComputingUs += compTime;
  /*if(cudaDev>-1&&torch::cuda::is_available()){
    // Move tensors to GPU 1
    result = result.to(torch::kCPU);
  }*/
  return result;
}
