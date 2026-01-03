/*! \file DistributedPartitionIndex.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_DISTRIBUTEDPARTITIONINDEX_H_
#define CANDY_INCLUDE_CANDY_DISTRIBUTEDPARTITIONINDEX_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <CANDY/AbstractIndex.h>
#include <CANDY/DistributedPartitionIndex/DistributedIndexWorker.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_container
 * @{
 */
/**
 * @class DistributedPartitionIndex CANDY/DistributedPartitionIndex.h
 * @brief A basic distributed index, works under generic data partition, allow configurable index of threads,
 * following round-robin insert and map-reduce query.
 * @todo consider an unblocked, optimized version of @ref insertTensor, as we did in @ref loadInitialTensor ?
 * @note special parameters
 *  - distributedWorker_algoTag The algo tag of this worker, String, default flat
 *  - distributedWorker_queueSize The input queue size of this worker, I64, default 10
 *  - distributedWorkers The number of paraller workers, I64, default 1;
 *  - vecDim, the dimension of vectors, default 768, I64
 *  - fineGrainedDistributedInsert, whether or not conduct the insert in an extremely fine-grained way, i.e., per-row, I64, default 0
 *  - sharedBuild whether let all sharding using shared build, 1, I64
 * @warning
 * Make sure you are using 2D tensors!
 * Not works well with python API
 */
class DistributedPartitionIndex : public CANDY::AbstractIndex {
 protected:
  int64_t distributedWorkers, insertIdx;
  std::vector<DistributedIndexWorkerPtr> workers;
  int64_t vecDim;
  int64_t fineGrainedDistributedInsert;
  int64_t sharedBuild;
  void insertTensorInline(torch::Tensor t);
  void partitionBuildInLine(torch::Tensor &t);
  void partitionLoadInLine(torch::Tensor &t);
 public:
  DistributedPartitionIndex() {

  }

  ~DistributedPartitionIndex() {

  }

  /**
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the tensor, some index need to be single row
  * @return bool whether the loading is successful
 */
  virtual bool loadInitialTensor(torch::Tensor &t);
  /**
    * @brief reset this index to inited status
    */
  virtual void reset();
  /**
   * @brief set the index-specfic config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief insert a tensor
   * @param t the tensor, some index need to be single row
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensor(torch::Tensor &t);

  /**
   * @brief delete a tensor
   * @param t the tensor, some index needs to be single row
   * @param k the number of nearest neighbors
   * @return bool whether the deleting is successful
   */
  virtual bool deleteTensor(torch::Tensor &t, int64_t k = 1);

  /**
   * @brief revise a tensor
   * @param t the tensor to be revised
   * @param w the revised value
   * @return bool whether the revising is successful
   * @note only support to delete and insert, no straightforward revision
   */
  virtual bool reviseTensor(torch::Tensor &t, torch::Tensor &w);

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
  * @brief search the k-NN of a query tensor, return the result tensors
  * @param t the tensor, allow multiple rows
  * @param k the returned neighbors
  * @return std::vector<torch::Tensor> the result tensor for each row of query
  */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);

  /**
  * @brief some extra set-ups if the index has HPC fetures
  * @return bool whether the HPC set-up is successful
  */
  virtual bool startHPC();
  /**
  * @brief some extra termination if the index has HPC fetures
  * @return bool whether the HPC termination is successful
  */
  virtual bool endHPC();
  /**
  * @brief set the frozen level of online updating internal state
  * @param frozenLv the level of frozen, 0 means freeze any online update in internal state
  * @return whether the setting is successful
  */
  virtual bool setFrozenLevel(int64_t frozenLv);
  /**
  * @brief offline build phase
  * @param t the tensor for offline build
  * @return whether the building is successful
  */
  virtual bool offlineBuild(torch::Tensor &t);
  /**
 * @brief a busy waitting for all pending operations to be done
 * @note in this index, there are may be some un-commited write due to the parallel queues
 * @return bool, whether the waitting is actually done;
 */
  virtual bool waitPendingOperations();
};

/**
 * @ingroup  CANDY_lib_container
 * @typedef DistributedPartitionIndexPtr
 * @brief The class to describe a shared pointer to @ref  DistributedPartitionIndex

 */
typedef std::shared_ptr<class CANDY::DistributedPartitionIndex> DistributedPartitionIndexPtr;
/**
 * @ingroup  CANDY_lib_container
 * @def newDistributedPartitionIndex
 * @brief (Macro) To creat a new @ref  DistributedPartitionIndex shared pointer.
 */
#define newDistributedPartitionIndex std::make_shared<CANDY::DistributedPartitionIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
