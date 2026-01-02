/*! \file FlatAMMIPIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <FlatAMMIPIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>
#include <Utils/IntelliLog.h>

bool CANDY::FlatAMMIPIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  if (faissMetric != faiss::METRIC_INNER_PRODUCT) {
    INTELLI_WARNING("I can only deal with inner product distance");
  }
  vecDim = cfg->tryI64("vecDim", 768, true);
  initialVolume = cfg->tryI64("initialVolume", 1000, true);
  expandStep = cfg->tryI64("expandStep", 100, true);
  sketchSize = cfg->tryI64("sketchSize", 10, true);
  DCOBatchSize = cfg->tryI64("DCOBatchSize", -1, true);
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
  dbTensor = torch::zeros({initialVolume, vecDim});

  lastNNZ = -1;
  return true;
}
static inline torch::Tensor amm_crs(torch::Tensor &a, torch::Tensor &b, int64_t ss) {
  int64_t n = a.size(1);
  // Probability distribution
  torch::Tensor probs = torch::ones(n) / n;  // default: uniform
  auto crsIndices = torch::multinomial(probs, ss, true);
  auto A_sampled = a.index_select(1, crsIndices);
  auto B_sampled = b.index_select(0, crsIndices);
  return torch::matmul(A_sampled, B_sampled);
}
static inline torch::Tensor amm_smppca(torch::Tensor &A, torch::Tensor &B, int64_t k2) {
  // Step 1: Input A:n1*d B:d*n2
  A = A.t(); // d*n1
  int64_t d = A.size(0);
  int64_t n1 = A.size(1);
  int64_t n2 = B.size(1);
  int64_t k = (int64_t) k2;

  // Step 2: Get sketched matrix
  torch::Tensor pi = 1 / std::sqrt(k) * torch::randn({k, d}); // Gaussian sketching matrix
  torch::Tensor A_tilde = torch::matmul(pi, A); // k*n1
  torch::Tensor B_tilde = torch::matmul(pi, B); // k*n2

  torch::Tensor A_tilde_B_tilde = torch::matmul(A_tilde.t(), B_tilde);

  // Step 3: Compute column norms
  // 3.1 column norms of A and B
  torch::Tensor col_norm_A = torch::linalg::vector_norm(A, 2, {0}, false, c10::nullopt); // ||Ai|| for i in [n1]
  torch::Tensor col_norm_B = torch::linalg::vector_norm(B, 2, {0}, false, c10::nullopt); // ||Bj|| for j in [n2]

  // 3.2 column norms of A_tilde and B_tilde
  torch::Tensor col_norm_A_tilde = torch::linalg::vector_norm(A_tilde, 2, {0}, false,
                                                              c10::nullopt); // ||Ai|| for i in [n1]
  torch::Tensor col_norm_B_tilde = torch::linalg::vector_norm(B_tilde, 2, {0}, false,
                                                              c10::nullopt); // ||Bj|| for j in [n2]

  // Step 4: Compute M_tilde
  torch::Tensor col_norm_A_col_norm_B = torch::matmul(col_norm_A.reshape({n1, 1}), col_norm_B.reshape({1, n2}));

  torch::Tensor col_norm_A_tilde_col_norm_B_tilde =
      torch::matmul(col_norm_A_tilde.reshape({n1, 1}), col_norm_B_tilde.reshape({1, n2}));
  torch::Tensor mask = (col_norm_A_tilde_col_norm_B_tilde == 0);
  col_norm_A_tilde_col_norm_B_tilde.masked_fill_(mask, 1e-6); // incase divide by 0 in next step

  torch::Tensor ratio = torch::div(col_norm_A_col_norm_B, col_norm_A_tilde_col_norm_B_tilde);

  torch::Tensor M_tilde = torch::mul(A_tilde_B_tilde, ratio);

  return M_tilde;
}
torch::Tensor CANDY::FlatAMMIPIndex::myMMInline(torch::Tensor &a, torch::Tensor &b, int64_t ss) {
  switch (ammType) {
    case 1: return amm_crs(a, b, ss);
    case 2: return amm_smppca(a, b, ss);
  }
  return torch::matmul(a, b);
}
void CANDY::FlatAMMIPIndex::reset() {
  lastNNZ = -1;
}
bool CANDY::FlatAMMIPIndex::insertTensor(torch::Tensor &t) {
  return INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &t, &lastNNZ, expandStep);
}

bool CANDY::FlatAMMIPIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  std::vector<faiss::idx_t> idxToDelete = searchIndex(t, k);
  std::vector<int64_t> &int64Vector = reinterpret_cast<std::vector<int64_t> &>(idxToDelete);
  return INTELLI::IntelliTensorOP::deleteRowsBufferMode(&dbTensor, int64Vector, &lastNNZ);
}

bool CANDY::FlatAMMIPIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  if (t.size(0) > w.size(0) || t.size(1) != w.size(1)) {
    return false;
  }
  int64_t rows = t.size(0);
  faiss::IndexFlat indexFlat(vecDim); // call constructor
  float *dbData = dbTensor.contiguous().data_ptr<float>();
  indexFlat.add(lastNNZ + 1, dbData); // add vectors to the index
  for (int64_t i = 0; i < rows; i++) {
    float distance;
    faiss::idx_t idx;
    auto rowI = t.slice(0, i, i + 1).contiguous();
    float *queryData = rowI.data_ptr<float>();
    indexFlat.search(1, queryData, 1, &distance, &idx);
    if (0 <= idx && idx <= lastNNZ) {
      auto rowW = w.slice(0, i, i + 1);
      INTELLI::IntelliTensorOP::editRows(&dbTensor, &rowW, (int64_t) idx);
    }
  }
  return true;
}
std::vector<faiss::idx_t> CANDY::FlatAMMIPIndex::knnInline(torch::Tensor &query, int64_t k, int64_t distanceBatchSize) {
  // Transpose the query tensor
  torch::Tensor transposed_query = query.t();

  // Load the database in batches
  int64_t batch_size = lastNNZ + 1;
  int64_t dbSize = lastNNZ + 1;
  if (distanceBatchSize > 0 && distanceBatchSize < lastNNZ + 1) {
    batch_size = distanceBatchSize;
  }
  torch::Tensor knn_indices;
  torch::Tensor distanceAll = torch::zeros({lastNNZ + 1, query.size(0)});
  int64_t distanceBufferPointer = -1;
  for (int64_t i = 0; i < dbSize; i += batch_size) {
    int64_t end_idx = std::min(i + batch_size, dbSize);
    torch::Tensor database_batch = dbTensor.slice(0, i, end_idx);
    // Compute matrix multiplication to get distances
    torch::Tensor distancesBatch = myMMInline(database_batch, transposed_query, sketchSize);
    INTELLI::IntelliTensorOP::appendRowsBufferMode(&distanceAll, &distancesBatch, &distanceBufferPointer);
  }
  // Get the indices of the k-nearest neighbors
  auto topk_tuple = torch::topk(distanceAll.t(), k, 1, true, true);
  torch::Tensor topk_indices = std::get<1>(topk_tuple);
  // Convert indices tensor to C++ vector
  std::vector<faiss::idx_t> knn_indices_vec;
  // Flatten the tensor
  torch::Tensor flattened_tensor = topk_indices.flatten();

  // Create std::vector<uint64_t> from the flattened tensor
  const int64_t *data_ptr = flattened_tensor.data_ptr<int64_t>();
  std::vector<faiss::idx_t> result(data_ptr, data_ptr + flattened_tensor.numel());

  return result;
}
std::vector<faiss::idx_t> CANDY::FlatAMMIPIndex::searchIndex(torch::Tensor q, int64_t k) {
  /*faiss::IndexFlat indexFlat(vecDim, faissMetric); // call constructor
  float *dbData = dbTensor.contiguous().data_ptr<float>();
  float *queryData = q.contiguous().data_ptr<float>();
  indexFlat.add(lastNNZ + 1, dbData); // add vectors to the index
  int64_t querySize = q.size(0);
  std::vector<faiss::idx_t> ru(k * querySize);
  std::vector<float> distance(k * querySize);
  indexFlat.search(querySize, queryData, k, distance.data(), ru.data());*/
  auto ru = knnInline(q, k, DCOBatchSize);
  return ru;
}

std::vector<torch::Tensor> CANDY::FlatAMMIPIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k) {
  int64_t tensors = idx.size() / k;
  std::vector<torch::Tensor> ru(tensors);

  for (int64_t i = 0; i < tensors; i++) {
    ru[i] = torch::zeros({k, vecDim});
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idx[i * k + j];
      if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1); }
    }
  }
  return ru;
}
torch::Tensor CANDY::FlatAMMIPIndex::rawData() {
  return dbTensor.slice(0, 0, lastNNZ + 1).contiguous();
}

std::vector<torch::Tensor> CANDY::FlatAMMIPIndex::searchTensor(torch::Tensor &q, int64_t k) {
  auto idx = searchIndex(q, k);
  return getTensorByIndex(idx, k);
}
