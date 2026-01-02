//
// Created by Isshin on 2024/1/8.
//

#ifndef CANDY_CLUSTERING_H
#define CANDY_CLUSTERING_H
#include "faiss/IndexFlat.h"
#include "Utils/AbstractC20Thread.hpp"
#include <vector>
#include <memory>
#include "Utils/IntelliTensorOP.hpp"
#include "Utils/ConfigMap.hpp"
namespace CANDY {
/**
 * @class ClusteringParameters CANDY/PQIndex/Clustering.h
 * @brief Class for the clustering parameters to be set before training/building
 */
class ClusteringParameters {
 public:
  /// number of clustering iterations
  int niter = 25;
  /// number of redoes
  int nredo = 1;
  /// re=train index after each iteration
  bool update_index = false;

  /// whether subset of centroids remain intact during each iteration
  bool frozen_centroids = false;
  int min_points_per_centroid = 39;
  int max_points_per_centroid = 256;
  int random_seed = 1919810;
  /// training batch size of codec decoder
  size_t decoded_block_size = 32768;
};
/**
 *  @class ClusteringIterationStats CANDY/PQIndex/Clustering.h
 *  @brief struct to record performance of clustering during iterations
 */
struct ClusteringIterationStats {
  float obj;
  double time;
  double time_search;
  int nsplit;
};
/**
 * @class Clustering CANDY/PQIndex/Clustering.h
 * @brief class for naive K-means clustering
 * @todo current build of centroids still depends on IndexFlatL2, perhaps re-implemented in a total tensor manner
 *  - @ref train
 */
class Clustering : ClusteringParameters {
 protected:
  INTELLI::ConfigMapPtr myCfg_ = nullptr;
  /// dimension of vectors
  int64_t vecDim_ = 0;
  /// number of centroids
  int64_t k_ = 256;

  /// centroids vector size : (k * d)
  torch::Tensor centroids_;
 public:
  std::vector<ClusteringIterationStats> iteration_stats_;
  Clustering(int64_t vecDim, int64_t k) : vecDim_(vecDim), k_(k) {
    centroids_ = torch::zeros({k_, vecDim_});
  };
  Clustering() = default;
  void reset();
  //bool setConfig(INTELLI::ConfigMapPtr cfg);
  auto getCentroids() -> torch::Tensor;
  /**
   * @brief train the clustering using tensor based on IndexFlatL2 with weights
   * @param nx number of input vectors
   * @param x_in input vectors as Tensor
   * @param index index upon which to search and evaluate during clustering
   * @param weights weights to compute centroids after assignment
   */
  void train(size_t nx, const torch::Tensor x_in, faiss::IndexFlatL2 *index, const torch::Tensor *weights);
  /**
   * @brief compute the imbalance factor of an assignment
   * @param n number of input vectors
   * @param k number of centroids
   * @param assign assignment of centroid clustering
   * @return imbalance factor of the assignment
   */
  double imbalance_factor(size_t n, int64_t k, int64_t *assign);
  /**
   * @brief compute the centroids of input vectors
   * @param d dim of vectors
   * @param k number of centroids
   * @param n number of input vectors
   * @param k_frozen number of frozen centroids which remain intact in this computation
   * @param x_in input vectors as Tensor
   * @param assign assignment array for n vectors
   * @param weights weights to compute centroids
   * @param hassign histogram of k centroids
   * @param centroids centroids after computation
   */
  void computeCentroids(
      int64_t d,
      int64_t k,
      size_t n,
      int64_t k_frozen,
      const torch::Tensor x_in,
      const int64_t *assign,
      const torch::Tensor *weights,
      torch::Tensor *hassign,
      torch::Tensor *centroids
  );
  /**
   * @brief balance the assignment by averaging between a big cluster and a null cluster
   * @param d dim of vectors
   * @param k number of centroids
   * @param n number of input vectors
   * @param k_frozen number of frozen centroids which remain intact
   * @param hassign histogram of k centroids
   * @param centroids centroids after computation
   * @return
   */
  int splitClusters(int64_t d,
                    int64_t k,
                    size_t n,
                    int64_t k_frozen,
                    torch::Tensor *hassign,
                    torch::Tensor *centroids
  );
};

}

#endif //CANDY_CLUSTERING_H
