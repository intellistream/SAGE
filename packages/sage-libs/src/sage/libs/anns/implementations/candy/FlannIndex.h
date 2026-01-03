//
// Created by Isshin on 2024/3/25.
//

#ifndef CANDY_FLANNINDEX_H
#define CANDY_FLANNINDEX_H
#include "FlannIndex/KdTree.h"
#include "FlannIndex/Kmeans.h"
#include <AbstractIndex.h>

namespace CANDY {
class FlannIndex : public AbstractIndex {
 public:

  flann_index_t flann_index = FLANN_KMEANS;
  FlannComponent *index;
  int64_t vecDim;
  int64_t allAuto = 0;
  /**
  * @brief set the index-specific config related to one index
  * @param cfg the config of this class
  * @return bool whether the configuration is successful
  */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);
  /**
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the tensor, some index need to be single row
  * @return bool whether the loading is successful
  */
  virtual bool loadInitialTensor(torch::Tensor &t);
  /**
  * @brief insert a tensor
  * @param t the tensor, accept multiple rows
  * @return bool whether the insertion is successful
  */
  virtual bool insertTensor(torch::Tensor &t);
  /**
  * @brief search the k-NN of a query tensor, return their index
  * @param t the tensor, allow multiple rows
  * @param k the returned neighbors
  * @return std::vector<faiss::idx_t> the index, follow faiss's order
  */
  virtual std::vector<faiss::idx_t> searchIndex(torch::Tensor q, int64_t k);
  /**
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);
  /**
   * @brief return a vector of tensors according to some index
   * @param idx the index, follow faiss's style, allow the KNN index of multiple queries
   * @param k the returned neighbors, i.e., will be the number of rows of each returned tensor
   * @return a vector of tensors, each tensor represent KNN results of one query in idx
   */
  virtual std::vector<torch::Tensor> getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k);
};
#define newFlannIndex std::make_shared<CANDY::FlannIndex>
}
#endif //CANDY_FLANNINDEX_H
