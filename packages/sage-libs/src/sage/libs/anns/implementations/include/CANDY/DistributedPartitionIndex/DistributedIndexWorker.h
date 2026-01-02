/*! \file DistributedIndexWorker.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_DistributedIndexWorker_H_
#define CANDY_INCLUDE_CANDY_DistributedIndexWorker_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <CANDY/IndexTable.h>
#include <Utils/SPSCQueue.hpp>
#include <CANDY/AbstractIndex.h>
#include <faiss/IndexFlat.h>
#include <ray/api.h>
#include <mutex>
namespace CANDY {

/**
 *  @ingroup  CANDY_lib_bottom_sub The support classes for index approaches
 * @{
 */
/**
 * @class DIW_RayWrapper CANDY/DistributedPartitionIndex/DistributedIndexWorker.h
 * @brief the ray wrapper of DistributedIndexWorker, most of its function will be ray-remote
 * - distributedWorker_algoTag The algo tag of this worker, String, default flat
 * - vecDim the dimension of vectors, I674, default 768
 */
class DIW_RayWrapper {
 protected:
  AbstractIndexPtr myIndexAlgo = nullptr;
  std::string myConfigString = "";
  int64_t vecDim = 0;
 public:
  DIW_RayWrapper() {}
  ~DIW_RayWrapper() {}
  static DIW_RayWrapper *FactoryCreate() { return new DIW_RayWrapper(); }
  /**
   * @brief set the config by using raw string
   * @param cfs the raw string
   * @return bool
   */
  bool setConfig(std::string cfs);
  /**
  * @brief insert a tensor
  * @param t the tensor packed in std::vector<uint8_t>
  * @return bool whether the insertion is successful
  */
  virtual bool insertTensor(std::vector<uint8_t> t);

  /**
   * @brief delete a tensor
   * @param t the tensor,  packed in std::vector<uint8_t>
   * @param k the number packed in std::vector<uint8_t>
   * @return bool whether the deleting is successful
   */
  virtual bool deleteTensor(std::vector<uint8_t> t, int64_t k = 1);

  /**
* @brief search the k-NN of a query tensor, return the result tensors
* @param q the tensor, packed in std::vector<uint8_t> allow multiple rows
* @param k the returned neighbors
* @return std::vector<std::vector<uint8_t>> the packed result tensor for each row of query
*/
  virtual std::vector<std::vector<uint8_t>> searchTensor(std::vector<uint8_t> t, int64_t k);

  bool reset();
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
  virtual bool offlineBuild(std::vector<uint8_t> t);
  /**
  *
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the tensor for offline build
  * @return whether the building is successful
  */
  virtual bool loadInitialTensor(std::vector<uint8_t> t);
  /**
   * @brief a busy waitting for all pending operations to be done
   * @note in this index, there are may be some un-commited write due to the parallel queues
   * @return bool, whether the waitting is actually done;
 */
  virtual bool waitPendingOperations();
};

/**
 * @class DistributedIndexWorker CANDY/DistributedPartitionIndex/DistributedIndexWorker.h
 * @brief A worker class of parallel index thread
 * @note special parameters
 * - parallelWorker_algoTag The algo tag of this worker, String, default flat
 * - parallelWorker_queueSize The input queue size of this worker, I64, default 10
 */
class DistributedIndexWorker {
 protected:

  /* int64_t myId = 0;
   int64_t vecDim = 0;*/
  ray::ActorHandle<DIW_RayWrapper> workerHandle;
  std::string cfgString;
  std::mutex m_mut;
  ray::ObjectRef<std::vector<std::vector<uint8_t>>> objRefUnblockedQuery;
  ray::ObjectRef<bool> objRefUnblockedBool;
  int64_t pendingTensors = 0;
  /**
  * @brief lock this worker
  */
  void lock() {
    while (!m_mut.try_lock());
  }
  /**
   * @brief unlock this worker
   */
  void unlock() {
    m_mut.unlock();
  }
  // AbstractIndexPtr myIndexAlgo = nullptr;
 public:

  DistributedIndexWorker() {

  }

  ~DistributedIndexWorker() {

  }

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
   * @brief some extra set-ups if the index has HPC fetures
   * @return bool whether the HPC set-up is successful
   */
  virtual bool startHPC();
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
  * @brief search the k-NN of a query tensor, return the result tensors
  * @param t the tensor, allow multiple rows
  * @param k the returned neighbors
  * @return std::vector<torch::Tensor> the result tensor for each row of query
  */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);
  /**
* @brief search the k-NN of a query tensor, without blocking the reset process
* @param q the tensor, packed in std::vector<uint8_t> allow multiple rows
* @param k the returned neighbors
* @return std::vector<std::vector<uint8_t>> the packed result tensor for each row of query
*/
  virtual void searchTensorUnblock(torch::Tensor &q, int64_t k);
  /**
* @brief search the k-NN of a query tensor, return the result tensors
* @param q the tensor, packed in std::vector<uint8_t> allow multiple rows
* @param k the returned neighbors
* @return std::vector<std::vector<uint8_t>> the packed result tensor for each row of query
*/
  virtual std::vector<torch::Tensor> getUnblockQueryResult(void);
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
  * @brief offline build phase in unblocked model
  * @param t the tensor for offline build
  */
  virtual void offlineBuildUnblocked(torch::Tensor &t);

  /**
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the tensor, some index need to be single row
  * @return bool whether the loading is successful
 */
  virtual bool loadInitialTensor(torch::Tensor &t);
  /**
 * @brief load initial tensor  in unblocked model
 * @param t the tensor for offline build
 */
  virtual void loadInitialTensorUnblocked(torch::Tensor &t);
  /**
* @brief a busy waitting for all pending operations to be done
* @note in this index, there are may be some un-commited write due to the parallel queues
* @return bool, whether the waitting is actually done;
*/
  virtual bool waitPendingOperations();
  /**
* @brief wait for the pending bool results, which are previously launched by unblocked manner
*/
  bool waitPendingBool(void);
};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef DistributedIndexWorkerPtr
 * @brief The class to describe a shared pointer to @ref  DistributedIndexWorker

 */
typedef std::shared_ptr<class CANDY::DistributedIndexWorker> DistributedIndexWorkerPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newDistributedIndexWorker
 * @brief (Macro) To creat a new @ref  DistributedIndexWorker shared pointer.
 */
#define newDistributedIndexWorker std::make_shared<CANDY::DistributedIndexWorker>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
