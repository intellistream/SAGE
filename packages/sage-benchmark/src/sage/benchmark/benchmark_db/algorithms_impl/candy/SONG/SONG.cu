/*
* Copyright (C) 2024 by the INTELLI team
 * Created by: Ziao Wang
 * Created on: 2024/11/18
 * Description: [Provide description here]
 */


// #include <Utils/UtilityFunctions.h>

#include "SONG.hpp"
#include <Utils/IntelliLog.h>
#include <ctime>
#include <chrono>
#include <cassert>
#include <vector>
#include <algorithm>
#include <utility>

bool CANDY::SONG::setConfig(INTELLI::ConfigMapPtr cfg) {
//  ANNSBase::setConfig(cfg);
  std::string metricType = cfg->tryString("metricType", "L2", true);
  faissMetric = metricType == "L2" ? faiss::METRIC_L2 : faiss::METRIC_INNER_PRODUCT;
  vecDim = cfg->tryI64("vecDim", 768, true);
  vecVolume = cfg->tryI64("vecVolume", 1000000, true);
  data = std::make_unique<SONG_KERNEL::Data> (vecVolume,vecDim);
  if (metricType == "L2") {
    graph = std::make_unique<SONG_KERNEL::KernelFixedDegreeGraph<0>> (data.get());
  } else if (metricType == "IP") {
    graph = std::make_unique<SONG_KERNEL::KernelFixedDegreeGraph<1>> (data.get());
  } else if (metricType == "cos") {
    graph = std::make_unique<SONG_KERNEL::KernelFixedDegreeGraph<2>> (data.get());
  } else {
    INTELLI_WARNING("Switch to L2");
    graph = std::make_unique<SONG_KERNEL::KernelFixedDegreeGraph<0>> (data.get());
  }
  // cudaDeviceSetLimit(cudaLimitMallocHeapSize,800*1024*1024);
  return true;
}

bool CANDY::SONG::insertTensor(torch::Tensor &t) {
  std::vector<std::vector<std::pair<int,SONG_KERNEL::value_t>>> vertexs;
  INTELLI_INFO("START CONVERT TENSOR TO VECTOR");
  convertTensorToVectorPairBatch(const_cast<torch::Tensor&>(t), vertexs);
  INTELLI_INFO("END CONVERT TENSOR TO VECTOR");
  INTELLI_INFO("START INSERT VERTEX");
  for (auto v : vertexs) {
    data->add(idx,v);
    graph->add_vertex(idx, v);
    // graph->add_vertex_new(idx, v);
    idx++;
  }
  INTELLI_INFO("END INSERT VERTEX");
  return true;
}

bool CANDY::SONG::deleteTensor(torch::Tensor &t, int64_t k) {
  return false;
}

bool CANDY::SONG::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  if (t.size(0) > w.size(0) || t.size(1) != w.size(1)) {
    return false;
  }
  // auto idx = findTopKClosest(t, 1, DCOBatchSize);
  // int64_t rows = t.size(0);
  // for (int64_t i = 0; i < rows; i++) {
  //   //auto rowI = t.slice(0, i, i + 1).contiguous();
  //   if (0 <= idx[i]) {
  //     auto rowW = w.slice(0, i, i + 1);
  //     dmBuffer.reviseTensor(idx[i], rowW);
  //     //INTELLI::IntelliTensorOP::editRows(&dbTensor, &rowW, (int64_t) idx);
  //   }
  // }
  return false;
}

std::vector<torch::Tensor> CANDY::SONG::searchTensor(torch::Tensor &q, int64_t k) {
  int query_size = q.size(0);
  std::vector<std::vector<std::pair<int,SONG_KERNEL::value_t>>> queries(query_size);
  std::vector<std::vector<SONG_KERNEL::idx_t>> result_id(query_size);
  convertTensorToVectorPairBatch(const_cast<torch::Tensor&>(q), queries);
  graph->search_top_k_batch(queries, k, result_id);
  std::vector<torch::Tensor> result_t(query_size);

  for (int i = 0; i < query_size; i++) {
    result_t[i] = torch::from_blob(result_id[i].data(), {k}, torch::kInt64).clone();

    // std::cout << "Query " << i << " results: ";
    // for (auto id : result_id[i]) std::cout << id << " ";
    // std::cout << std::endl;

  }
  return result_t;
}

void CANDY::SONG::convertTensorToVectorPair(torch::Tensor &t,
                                      std::vector<std::pair<int,SONG_KERNEL::value_t>> &res) {
    int64_t cols = t.size(1);
    res.resize(cols);
    for(int64_t i = 0; i < cols; i++) {
        res[i] = std::make_pair(i, t[0][i].item<SONG_KERNEL::value_t>());
    }
}

void CANDY::SONG::convertTensorToVectorPairBatch(torch::Tensor &ts,
                                    std::vector<std::vector<std::pair<int,SONG_KERNEL::value_t>>> &res) {
    int64_t rows = ts.size(0);
    if (res.size() != rows) {
        res.resize(rows);
    }
    for(int64_t i = 0; i < rows; i++) {
        auto row = ts.slice(0, i, i + 1);
        convertTensorToVectorPair(row, res[i]);
    }
}

bool CANDY::SONG::resetIndexStatistics() {
  gpuComputingUs = 0;
  gpuCommunicationUs = 0;
  return true;
}

INTELLI::ConfigMapPtr CANDY::SONG::getIndexStatistics() {
  auto cfg = AbstractIndex::getIndexStatistics();
  // cfg->edit("hasExtraStatistics", (int64_t) 1);
  // /**
  //  * @brief count of memory access
  //  */
  // cfg->edit("totalMemReadCnt", (int64_t) dmBuffer.getMemoryReadCntTotal());
  // cfg->edit("missMemReadCnt", (int64_t) dmBuffer.getMemoryReadCntMiss());
  // double memMissHitRead = dmBuffer.getMemoryReadCntMiss();
  // memMissHitRead = memMissHitRead / dmBuffer.getMemoryReadCntTotal();
  // cfg->edit("memMissRead", (double) memMissHitRead);
  // cfg->edit("totalMemWriteCnt", (int64_t) dmBuffer.getMemoryWriteCntTotal());
  // cfg->edit("missMemWriteCnt", (int64_t) dmBuffer.getMemoryWriteCntMiss());
  // double memMissHitWrite = dmBuffer.getMemoryWriteCntMiss();
  // memMissHitWrite = memMissHitWrite / dmBuffer.getMemoryWriteCntTotal();
  // cfg->edit("memMissWrite", (double) memMissHitWrite);
  // /**
  //  * @brief gpu statistics
  //  */
  // if (cudaDevice > -1 && torch::cuda::is_available()) {
  //   cfg->edit("gpuCommunicationUs", (int64_t) gpuCommunicationUs);
  //   cfg->edit("gpuComputingUs", (int64_t) gpuComputingUs);
  // } else {
  //   cfg->edit("cpuComputingUs", (int64_t) gpuComputingUs);
  // }
  return cfg;
}
