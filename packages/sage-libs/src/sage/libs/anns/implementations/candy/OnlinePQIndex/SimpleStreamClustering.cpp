//
// Created by tony on 11/01/24.
//

#include <OnlinePQIndex/SimpleStreamClustering.h>
#include <Utils/IntelliLog.h>
bool CANDY::SimpleStreamClustering::buildCentroids(torch::Tensor &trainSet,
                                                   int64_t k,
                                                   int64_t maxIterations,
                                                   DistanceFunction_t distanceFunc,
                                                   bool usingCuda) {
  // Initialize centroids randomly
  torch::manual_seed(42);
  // Probability distribution
  int64_t n = trainSet.size(0);
  torch::Tensor probs = torch::ones(n) / n;  // default: uniform

  // Sample k indices from range 0 to n for given probability distribution
  torch::Tensor indices = torch::multinomial(probs, k, true);
  // return indices;
  auto centroids = trainSet.index_select(0, indices);
  auto data = trainSet;
  if (usingCuda) {
    centroids = centroids.to(torch::kCUDA);
    data = data.to(torch::kCUDA);
  }
  for (int64_t iteration = 0; iteration < maxIterations; ++iteration) {
    // Assign each data point to the nearest centroid
    torch::Tensor distances = distanceFunc(data, centroids);
    torch::Tensor labels = std::get<1>(torch::min(distances, /*dim=*/1));

    // Update centroids based on the mean of points in each cluster
    for (int64_t cluster = 0; cluster < k; ++cluster) {
      auto rowMask = labels.eq(cluster);
      torch::Tensor clusterPoints = data.index({rowMask.nonzero().squeeze()});
      if (clusterPoints.size(0) > 0) {
        centroids[cluster] = clusterPoints.mean(0);
      }
    }
    INTELLI_INFO("Done clustering iteration " + std::to_string(iteration) + "/" + std::to_string(maxIterations));
  }
  if (usingCuda) {
    myCentroids = centroids.to(torch::kCPU);
  } else {
    myCentroids = centroids;
  }
  myDataCntInCentroid = std::vector<int64_t>((size_t) k, 0);
  return true;
}
bool CANDY::SimpleStreamClustering::loadCentroids(torch::Tensor &externCentroid) {
  int64_t k = externCentroid.size(0);
  if (k <= 0) {
    return false;
  }
  myDataCntInCentroid = std::vector<int64_t>((size_t) k, 0);
  myCentroids = externCentroid.clone();
  return true;
}
int64_t CANDY::SimpleStreamClustering::classifySingleRow(torch::Tensor &rowTensor, DistanceFunction_t distanceFunc) {
  torch::Tensor distances = distanceFunc(rowTensor, myCentroids);
  int64_t clusterIndex = std::get<1>(torch::min(distances, /*dim=*/1))[0].item<int64_t>();
  return clusterIndex;
}
std::vector<int64_t> CANDY::SimpleStreamClustering::classifyMultiRow(torch::Tensor &rowsTensor,
                                                                     DistanceFunction_t distanceFunc) {
  torch::Tensor distances = distanceFunc(rowsTensor, myCentroids);
  torch::Tensor labels = std::get<1>(torch::min(distances, /*dim=*/1));
  auto tensor_a = labels.contiguous();
  std::vector<int64_t> vector_a(tensor_a.data_ptr<int64_t>(), tensor_a.data_ptr<int64_t>() + tensor_a.numel());
  return vector_a;
}
bool CANDY::SimpleStreamClustering::addSingleRow(torch::Tensor &rowTensor,
                                                 int64_t frozenLevel,
                                                 CANDY::UpdateFunction_t insertFunc, DistanceFunction_t distanceFunc) {
  int64_t clusterIdx = classifySingleRow(rowTensor, distanceFunc);
  myDataCntInCentroid[(size_t) clusterIdx]++;
  if (frozenLevel > 0) {
    auto centroidTensor = myCentroids.slice(0, clusterIdx, clusterIdx + 1);
    int64_t cnt = myDataCntInCentroid[(size_t) clusterIdx];
    insertFunc(&rowTensor, &centroidTensor, cnt);
    myCentroids.slice(0, clusterIdx, clusterIdx + 1) = centroidTensor;
  }
  return true;
}
bool CANDY::SimpleStreamClustering::addSingleRowWithIdx(torch::Tensor &rowTensor,
                                                        int64_t clusterIdx,
                                                        int64_t frozenLevel,
                                                        CANDY::UpdateFunction_t insertFunc,
                                                        CANDY::DistanceFunction_t distanceFunc) {
  myDataCntInCentroid[(size_t) clusterIdx]++;
  if (frozenLevel > 0) {
    auto centroidTensor = myCentroids.slice(0, clusterIdx, clusterIdx + 1);
    int64_t cnt = myDataCntInCentroid[(size_t) clusterIdx];
    insertFunc(&rowTensor, &centroidTensor, cnt);
    myCentroids.slice(0, clusterIdx, clusterIdx + 1) = centroidTensor;
  }
  return true;
}

bool CANDY::SimpleStreamClustering::deleteSingleRow(torch::Tensor &rowTensor,
                                                    int64_t frozenLevel,
                                                    CANDY::UpdateFunction_t deleteFunc,
                                                    DistanceFunction_t distanceFunc) {
  int64_t clusterIdx = classifySingleRow(rowTensor, distanceFunc);
  myDataCntInCentroid[(size_t) clusterIdx]--;
  if (frozenLevel > 0) {
    auto centroidTensor = myCentroids.slice(0, clusterIdx, clusterIdx + 1);
    int64_t cnt = myDataCntInCentroid[(size_t) clusterIdx];
    deleteFunc(&rowTensor, &centroidTensor, cnt);
    myCentroids.slice(0, clusterIdx, clusterIdx + 1) = centroidTensor;
  }
  return true;
}
bool CANDY::SimpleStreamClustering::deleteSingleRowWithIdx(torch::Tensor &rowTensor,
                                                           int64_t clusterIdx,
                                                           int64_t frozenLevel,
                                                           CANDY::UpdateFunction_t deleteFunc,
                                                           CANDY::DistanceFunction_t distanceFunc) {
  myDataCntInCentroid[(size_t) clusterIdx]--;
  if (frozenLevel > 0) {
    auto centroidTensor = myCentroids.slice(0, clusterIdx, clusterIdx + 1);
    int64_t cnt = myDataCntInCentroid[(size_t) clusterIdx];
    deleteFunc(&rowTensor, &centroidTensor, cnt);
    myCentroids.slice(0, clusterIdx, clusterIdx + 1) = centroidTensor;
  }
  return true;
}
