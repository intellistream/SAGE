/*! \file OnlinePQIndex.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_ONLINEPQINDEX_H_
#define CANDY_INCLUDE_CANDY_ONLINEPQINDEX_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <faiss/IndexFlat.h>
#include <AbstractIndex.h>
#include <OnlinePQIndex/SimpleStreamClustering.h>
#include <OnlinePQIndex/IVFTensorEncodingList.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_bottom The main body and interfaces of library function
 * @{
 */
/**
 * @class OnlinePQIndex CANDY/OnlinePQIndex.h
 * @brief The class of online PQ approach, using IVF-style coarse-grained + fine-grained quantizers
 * @note currently single thread
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - coarseGrainedClusters,the number of coarse-grained clusters, default 4096, I64
 * - fineGrainedClusters,the number of fine-grained clusters in each sub quantizer, default 256, 1~256 I64
 * - subQuantizers, the number of sub quantizers, default 8, I64
 * - coarseGrainedBuiltPath, the path of built coarse grained centroids, default "OnlinePQIndex_coarse.rbt", String
 * - fineGrainedBuiltPath, the path of built fine grained centroids, default "OnlinePQIndex_fine.tbt", String
 * - cudaBuild, whether using cuda in building phase, default 0, I64
 * - maxBuildIteration, the maxium iterations of buildoing, default 1000, I64
 * - candidateTimes, the times of k to determine minimum candidates, default 1 ,I64
 * - disableADC, set this to 1 will disable ADC or residential computing and go back to IVFPQ, default 0 (means IVFADC mode), I64
 */
class OnlinePQIndex : public AbstractIndex {
 protected:
  INTELLI::ConfigMapPtr myCfg = nullptr;
  int64_t lastNNZ = 0;
  int64_t vecDim = 0, coarseGrainedClusters = 4096, subQuantizers = 8, fineGrainedClusters = 256;
  int64_t cudaBuild = 0;
  int64_t maxBuildIteration = 1000;
  int64_t candidateTimes = 1;
  int64_t disableADC = 0;
  bool isBuilt = false;
  std::string coarseGrainedBuiltPath, fineGrainedBuiltPath;
  SimpleStreamClusteringPtr coarseQuantizerPtr;
  std::vector<SimpleStreamClusteringPtr> fineQuantizerPtrs;
  std::vector<int64_t> subQuantizerStartPos;
  std::vector<int64_t> subQuantizerEndPos;
  int64_t frozenLevel = 0;
  bool tryLoadQuantizers(void);
  std::vector<int64_t> coarseGrainedEncode(torch::Tensor &t, torch::Tensor *residential);
  std::vector<std::vector<uint8_t>> fineGrainedEncode(torch::Tensor &residential);
  IVFTensorEncodingList IVFList;

  /**
   * @brief the inline function of deleting  rows
   * @param t the tensor, multiple rows
   * @return bool whether the deleting is successful
   */
  bool deleteRowsInline(torch::Tensor &t);
 public:
  OnlinePQIndex() {

  }

  ~OnlinePQIndex() {

  }

  /**
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and is different from @ref insertTensor for this one:
  * - The frozen level is forced to be 0 since the data is initial data
  * - Will try to build clusters from scratch if they are not successfully loaded
  * @param t the tensor, some index need to be single row
  * @return bool whether the loading is successful
 */
  virtual bool loadInitialTensor(torch::Tensor &t);
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
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);
  /**
  * @brief offline build phase
  * @note In this index, call offlineBuild will do the following'
  * - Build cluster centroids of both coarse grained and fine grained quantizers from t
  * - Save the centroids to raw binary tensor files, the names are as specified in 'coarseGrainedBuiltPath' and 'fineGrainedBuiltPath
  * @param t the tensor for offline build
  * @return whether the building is successful
  */
  virtual bool offlineBuild(torch::Tensor &t);
  /**
   * @brief set the frozen level of online updating internal state
   * @param frozenLv the level of frozen, 0 means freeze any online update in internal state
   * @note the frozen levels
   * - 0 frozen everything
   * - 1 frozen fine-grained clusters
   * - 2 frozen coarse-grained clusters
   * - >=3 frozen nothing
   * @return whether the setting is successful
   */
  virtual bool setFrozenLevel(int64_t frozenLv);

};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef OnlinePQIndexPtr
 * @brief The class to describe a shared pointer to @ref  OnlinePQIndex

 */
typedef std::shared_ptr<class CANDY::OnlinePQIndex> OnlinePQIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newOnlinePQIndex
 * @brief (Macro) To creat a new @ref  OnlinePQIndex shared pointer.
 */
#define newOnlinePQIndex std::make_shared<CANDY::OnlinePQIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
