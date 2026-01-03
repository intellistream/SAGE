/*! \file HNSWNaiveIndex.h*/
//
// Created by Isshin on 2024/1/16.
//

#ifndef CANDY_HNSWNAIVEINDEX_H
#define CANDY_HNSWNAIVEINDEX_H
#include <AbstractIndex.h>
#include <FlatIndex.h>
#include <HNSWNaive/HNSW.h>
namespace CANDY {
/**
 * @class HNSWNaiveIndex CANDY/HNSWNaiveIndex.h
 * @brief The class of a HNSW index approach, store the data in each vertex
 * @note currently single thread
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - maxConnection, number of maximum neighbor connection at each level, default
 * 32, I64
 * - is_NSW, whether initialized as an NSW index, default 0 (init as HNSW), I64
 */
class HNSWNaiveIndex : public AbstractIndex {
public:
  HNSW hnsw;
  bool is_NSW;

  bool is_local_lvq = true;
  FlatIndex *storage = nullptr;
  INTELLI::ConfigMapPtr myCfg = nullptr;

  typedef int64_t opt_mode_t;
  opt_mode_t opt_mode_ = OPT_VANILLA;
  faiss::MetricType faissMetric = faiss::METRIC_L2;

  int64_t vecDim;
  /// Number of neighbors in HNSW structure
  int64_t M_ = 32;
  /// Number of all vectors
  int64_t ntotal = 0;

  int64_t adSampling_step = 32;
  float adSampling_epsilon0 = 1.0;

  HNSWNaiveIndex(){};

  /**
   * @brief set the index-specific config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief insert a tensor
   * @param t the tensor, accept multiple rows
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensor(torch::Tensor &t);

  /**
   * @brief delete a tensor
   * @param t the tensor, recommend single row
   * @param k the number of nearest neighbors
   * @return bool whether the deleting is successful
   */
  virtual bool deleteTensor(torch::Tensor &t, int64_t k = 1);

  /**
   * @brief revise a tensor
   * @param t the tensor to be revised, recommend single row
   * @param w the revised value
   * @return bool whether the revising is successful
   */
  virtual bool reviseTensor(torch::Tensor &t, torch::Tensor &w);

  /**
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);

    /**
     * @brief search the k-NN of a query tensor, return their index
     * @param t the tensor, allow multiple rows
     * @param k the returned neighbors
     * @return std::vector<faiss::idx_t> the index, follow faiss's order
     */
    virtual std::vector<faiss::idx_t> searchIndex(torch::Tensor q, int64_t k);

};
#define newHNSWNaiveIndex std::make_shared<CANDY::HNSWNaiveIndex>
#define newNSWIndex std::make_shared<CANDY::HNSWNaiveIndex>
// END OF NAMESPACE
} // namespace CANDY

#endif // CANDY_HNSWNAIVEINDEX_H
