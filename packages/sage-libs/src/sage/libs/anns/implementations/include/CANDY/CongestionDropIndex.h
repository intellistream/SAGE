/*! \file CongestionDropIndex.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_CongestionDropINDEX_H_
#define CANDY_INCLUDE_CANDY_CongestionDropINDEX_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <CANDY/AbstractIndex.h>
#include <CANDY/CongestionDropIndex/CongestionDropIndexWorker.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_container
 * @{
 */
/**
 * @class CongestionDropIndex CANDY/CongestionDropIndex.h
 * @brief A container index to evaluate other bottom index, will just drop the data if congestion occurs, also support the data sharding parallelism
 * @note When there is only one worker, will only  R/W lock for concurrency control, no sequential guarantee, different from @ref ParallelPartitionIndex
 * @warning Don't mix the usage of tensor-only I/O and tensor-string hybrid I/O in one indexing class
 * @warning remember to call @ref starHPC and @ref endHPC
 * @note special parameters
 *  - congestionDropWorker_algoTag The algo tag of this worker, String, default flat
 *  - congestionDropWorker_queueSize The input queue size of this worker, I64, default 10
 *  - parallelWorks The number of paraller workers, I64, default 1 (set this to less than 0 will use max hardware_concurrency);
 *  - vecDim, the dimension of vectors, default 768, I64
 *  - fineGrainedParallelInsert, whether or not conduct the insert in an extremely fine-grained way, i.e., per-row, I64, default 0
 *  - congestionDrop, whether or not drop the data when congestion occurs, I64, default 1
 *  - sharedBuild whether let all sharding using shared build, 1, I64
 *  - singleWorkerOpt whether optimize the searching under single worker, 1 I64
 * @warnning
 * Make sure you are using 2D tensors!
 */
class CongestionDropIndex : public CANDY::AbstractIndex {
 protected:
  int64_t parallelWorkers, insertIdx;
  std::vector<CongestionDropIndexWorkerPtr> workers;
  int64_t vecDim;
  int64_t fineGrainedParallelInsert;
  int64_t sharedBuild;
  int64_t singleWorkerOpt;
  void insertTensorInline(torch::Tensor &t);
  void partitionBuildInLine(torch::Tensor &t);
  void partitionLoadInLine(torch::Tensor &t);
  void insertStringInline(torch::Tensor &t, std::vector<string> &s);
  void partitionLoadStringInLine(torch::Tensor &t, std::vector<string> &s);
 public:
  std::vector<TensorListIdxQueuePtr> reduceQueue;
  std::vector<TensorStrVecQueuePtr> reduceStrQueue;
  CongestionDropIndex() {

  }

  ~CongestionDropIndex() {

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
 * @brief a busy waiting for all pending operations to be done
 * @note in this index, there are may be some un-commited write due to the parallel queues
 * @return bool, whether the waiting is actually done;
 */
  virtual bool waitPendingOperations();

  /**
  * @brief load the initial tensors of a data base along with its string objects, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the tensor, some index need to be single row
   *  * @param strs the corresponding list of strings
  * @return bool whether the loading is successful
  */
  virtual bool loadInitialStringObject(torch::Tensor &t, std::vector<std::string> &strs);
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
  /**
* @brief search the k-NN of a query tensor, return the linked string objects and original tensors
* @param t the tensor, allow multiple rows
* @param k the returned neighbors
* @return std::tuple<std::vector<torch::Tensor>,std::vector<std::vector<std::string>>>
*/
  virtual std::tuple<std::vector<torch::Tensor>, std::vector<std::vector<std::string>>> searchTensorAndStringObject(
      torch::Tensor &q,
      int64_t k);
};

/**
 * @ingroup  CANDY_lib_container
 * @typedef CongestionDropIndexPtr
 * @brief The class to describe a shared pointer to @ref  CongestionDropIndex

 */
typedef std::shared_ptr<class CANDY::CongestionDropIndex> CongestionDropIndexPtr;
/**
 * @ingroup  CANDY_lib_container
 * @def newCongestionDropIndex
 * @brief (Macro) To creat a new @ref  CongestionDropIndex shared pointer.
 */
#define newCongestionDropIndex std::make_shared<CANDY::CongestionDropIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
