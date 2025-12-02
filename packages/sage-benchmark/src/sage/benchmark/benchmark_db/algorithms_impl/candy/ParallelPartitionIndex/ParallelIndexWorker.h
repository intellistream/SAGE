/*! \file ParallelIndexWorker.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_ParallelIndexWorker_H_
#define CANDY_INCLUDE_CANDY_ParallelIndexWorker_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <IndexTable.h>
#include <Utils/SPSCQueue.hpp>
#include <AbstractIndex.h>
#include <faiss/IndexFlat.h>
namespace CANDY {
/**
 * @class TensorIdxPair
 * @brief The class to define a tensor along with some idx
 */
class TensorIdxPair {
 public:
  TensorIdxPair() {}
  ~TensorIdxPair() {}
  torch::Tensor t;
  int64_t idx;
  TensorIdxPair(torch::Tensor _t, int64_t _idx) {
    t = _t;
    idx = _idx;

  }
};
class TensorListIdxPair {
 public:
  TensorListIdxPair() {}
  ~TensorListIdxPair() {}
  std::vector<torch::Tensor> t;
  int64_t idx, querySeq;

  TensorListIdxPair(std::vector<torch::Tensor> &_t, int64_t _idx, int64_t _seq) {
    t = _t;
    idx = _idx;
    querySeq = _seq;
  }
};
class TensorStrPair {
 public:
  TensorStrPair() {}
  ~TensorStrPair() {}
  torch::Tensor t;
  int64_t idx;
  std::vector<std::string> strObj;
  TensorStrPair(torch::Tensor _t, int64_t _idx) {
    t = _t;
    idx = _idx;
  }
  TensorStrPair(torch::Tensor _t, int64_t _idx, std::vector<std::string> &str) {
    t = _t;
    idx = _idx;
    strObj = str;
  }
};
class TensorStrVecPair {
 public:
  TensorStrVecPair() {}
  ~TensorStrVecPair() {}
  std::vector<torch::Tensor> t;
  int64_t idx, querySeq;
  std::vector<std::vector<std::string>> strObjs;
  TensorStrVecPair(std::vector<torch::Tensor> &_t,
                   int64_t _idx,
                   int64_t _seq,
                   std::vector<std::vector<std::string>> str) {
    t = _t;
    idx = _idx;
    querySeq = _seq;
    strObjs = str;
  }
  TensorStrVecPair(std::vector<torch::Tensor> &_t, int64_t _idx, int64_t _seq) {
    t = _t;
    idx = _idx;
    querySeq = _seq;
  }
};
typedef std::shared_ptr<INTELLI::SPSCQueue<torch::Tensor>> TensorQueuePtr;
typedef std::shared_ptr<INTELLI::SPSCQueue<CANDY::TensorIdxPair>> TensorIdxQueuePtr;
typedef std::shared_ptr<INTELLI::SPSCQueue<CANDY::TensorListIdxPair>> TensorListIdxQueuePtr;
typedef std::shared_ptr<INTELLI::SPSCQueue<int64_t>> CmdQueuePtr;
typedef std::shared_ptr<INTELLI::SPSCQueue<CANDY::TensorIdxPair>> TensorIdxQueuePtr;
typedef std::shared_ptr<INTELLI::SPSCQueue<CANDY::TensorListIdxPair>> TensorListIdxQueuePtr;
typedef std::shared_ptr<INTELLI::SPSCQueue<CANDY::TensorStrPair>> TensorStrQueuePtr;
typedef std::shared_ptr<INTELLI::SPSCQueue<CANDY::TensorStrVecPair>> TensorStrVecQueuePtr;
/**
 *  @defgroup  CANDY_lib_bottom_sub The support classes for index approaches
 * @{
 */
/**
 * @class ParallelIndexWorker CANDY/ParallelPartitionIndex/ParallelIndexWorker.h
 * @brief A worker class of parallel index thread
 * @note Concurrency policy is strictly read after write
 * @note special parameters
 * - parallelWorker_algoTag The algo tag of this worker, String, default flat
 * - parallelWorker_queueSize The input queue size of this worker, I64, default 10
 * - vecDim the dimension of vectors, I674, default 768
 * - congestionDrop, whether or not drop the data when congestion occurs, I64, default 0
 */
class ParallelIndexWorker : public INTELLI::AbstractC20Thread {
 protected:
  TensorQueuePtr insertQueue, reviseQueue0, reviseQueue1, buildQueue, initialLoadQueue;
  TensorIdxQueuePtr deleteQueue, queryQueue, deleteStrQueue;
  TensorStrQueuePtr initialStrQueue, insertStrQueue;
  TensorIdxQueuePtr queryStrQueue;

  CmdQueuePtr cmdQueue;
  int64_t myId = 0;
  int64_t vecDim = 0;
  int64_t congestionDrop = 1;
  int64_t ingestedVectors = 0;
  int64_t singleWorkerOpt;
  std::mutex m_mut;
  /**
   * @brief The inline 'main" function of thread, as an interface
   * @note Normally re-write this in derived classes
   */
  virtual void inlineMain();
  AbstractIndexPtr myIndexAlgo = nullptr;
 public:
  TensorListIdxQueuePtr reduceQueue;
  TensorStrVecQueuePtr reduceStrQueue;
  ParallelIndexWorker() {

  }

  ~ParallelIndexWorker() {

  }
  virtual void setReduceQueue(TensorListIdxQueuePtr rq) {
    reduceQueue = rq;
  }
  virtual void setReduceStrQueue(TensorStrVecQueuePtr rq) {
    reduceStrQueue = rq;
  }
  virtual void setId(int64_t _id) {
    myId = _id;
  }

  virtual bool waitPendingOperations() {
    while (!m_mut.try_lock());
    m_mut.unlock();
    return true;
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
   * @brief revise a tensor
   * @param t the tensor to be revised
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
  virtual void pushSearch(torch::Tensor q, int64_t k);
  virtual void pushSearchStr(torch::Tensor q, int64_t k);
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
 * @ingroup  CANDY_lib_bottom
 * @typedef ParallelIndexWorkerPtr
 * @brief The class to describe a shared pointer to @ref  ParallelIndexWorker

 */
typedef std::shared_ptr<class CANDY::ParallelIndexWorker> ParallelIndexWorkerPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newParallelIndexWorker
 * @brief (Macro) To creat a new @ref  ParallelIndexWorker shared pointer.
 */
#define newParallelIndexWorker std::make_shared<CANDY::ParallelIndexWorker>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
