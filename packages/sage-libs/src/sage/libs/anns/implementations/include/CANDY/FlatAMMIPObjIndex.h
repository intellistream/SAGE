/*! \file FlatAMMIPObjIndex.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_FlatAMMIPObjIndex_H_
#define CANDY_INCLUDE_CANDY_FlatAMMIPObjIndex_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <faiss/IndexFlat.h>
#include <CANDY/AbstractIndex.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_bottom The main body and interfaces of library function
 * @{
 */
/**
 * @class FlatAMMIPObjIndex CANDY/FlatAMMIPObjIndex.h
 * @brief Similar to @ref FlatAMMIPIndex, but additionally has object storage (currently only string)
 * @note Only support inner product distance
 * @note currently single thread
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - initialVolume, the initial volume of inline database tensor, default 1000, I64
 * - expandStep, the step of expanding inline database, default 100, I64
 * - sketchSize, the sketch size of amm, default 10, I64
 * - DCOBatchSize, the batch size of internal distance comparison operation (DCO), default -1 (full data once), I64
 * - ammAlgo, the amm algorithm used for compute distance, default mm, String, can be the following
    * - mm the original torch::matmul
    * - crs column row sampling
    * - smp-pca the smp-pca algorithm
 */
class FlatAMMIPObjIndex : public AbstractIndex {
 protected:
  INTELLI::ConfigMapPtr myCfg = nullptr;
  torch::Tensor dbTensor, objTensor;
  int64_t lastNNZ = 0;
  int64_t lastNNZObj = 0;
  int64_t vecDim = 0, initialVolume = 1000, expandStep = 100;
  int64_t ammType = 0;
  int64_t sketchSize = 10;
  int64_t DCOBatchSize = -1;
  torch::Tensor myMMInline(torch::Tensor &a, torch::Tensor &b, int64_t ss = 10);
  std::vector<faiss::idx_t> knnInline(torch::Tensor &query, int64_t k, int64_t distanceBatch = -1);
 public:
  FlatAMMIPObjIndex() {

  }

  ~FlatAMMIPObjIndex() {

  }

  /**
    * @brief reset this index to inited status
    */
  virtual void reset();
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
  /**
   * @brief return the rawData of tensor
   * @return The raw data stored in tensor
   */
  virtual torch::Tensor rawData();
  /**
   * @brief return the size of ingested tensors
   * @return
   */
  virtual int64_t size() {
    return lastNNZ + 1;
  }
  /**
   * @brief insert a string object
   * @note This is majorly an online function
   * @param t the tensor, some index need to be single row
   * @param strs the corresponding list of strings
   * @return bool whether the insertion is successful
   */
  virtual bool insertStringObject(torch::Tensor &t, std::vector<std::string> &strs);

  /**
   * @brief  delete tensor along with its corresponding string object
   * @note This is majorly an online function
   * @param t the tensor, some index need to be single row
   * @param k the number of nearest neighbors
   * @return bool whether the delet is successful
   */
  virtual bool deleteStringObject(torch::Tensor &t, int64_t k = 1);

  /**
 * @brief search the k-NN of a query tensor, return the linked string objects
 * @param t the tensor, allow multiple rows
 * @param k the returned neighbors
 * @return std::vector<std::vector<std::string>> the result object for each row of query
 */
  virtual std::vector<std::vector<std::string>> searchStringObject(torch::Tensor &q, int64_t k);
};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef FlatAMMIPObjIndexPtr
 * @brief The class to describe a shared pointer to @ref  FlatAMMIPObjIndex

 */
typedef std::shared_ptr<class CANDY::FlatAMMIPObjIndex> FlatAMMIPObjIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newFlatAMMIPObjIndex
 * @brief (Macro) To creat a new @ref  FlatAMMIPObjIndex shared pointer.
 */
#define newFlatAMMIPObjIndex std::make_shared<CANDY::FlatAMMIPObjIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
