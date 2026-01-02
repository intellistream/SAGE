/*! \file CongestionDropIndexWorker.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_CongestionDropIndexWorker_H_
#define CANDY_INCLUDE_CANDY_CongestionDropIndexWorker_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <CANDY/IndexTable.h>
#include <Utils/SPSCQueue.hpp>
#include <CANDY/AbstractIndex.h>
#include <faiss/IndexFlat.h>
#include <CANDY/ParallelPartitionIndex/ParallelIndexWorker.h>
namespace CANDY {
/**
 *  @defgroup  CANDY_lib_bottom_sub The support classes for index approaches
 * @{
 */
/**
 * @class CongestionDropIndexWorker CANDY/ParallelPartitionIndex/CongestionDropIndexWorker.h
 * @brief A worker class to container bottom indexings, will just drop new element if congestion occurs
 * @note special parameters
 * - congestionDropWorker_algoTag The algo tag of this worker, String, default flat
 * - congestionDropWorker_queueSize The input queue size of this worker, I64, default 10
 * - congestionDrop, whether or not drop the data when congestion occurs, I64, default 1
 * -vecDim the dimension of vectors, I674, default 768
 */
class CongestionDropIndexWorker : public CANDY::ParallelIndexWorker {
 protected:
  int64_t forceDrop = 1;
 public:
  TensorListIdxQueuePtr reduceQueue;
  CongestionDropIndexWorker() {

  }

  ~CongestionDropIndexWorker() {

  }
  /**
    * @brief insert a tensor
    * @param t the tensor, some index need to be single row
    * @return bool whether the insertion is successful
    */
  virtual bool insertTensor(torch::Tensor &t);

  /**
   * @brief set the index-specfic config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);
  /**
  * @brief search the k-NN of a query tensor, return the result tensors
  * @param t the tensor, allow multiple rows
  * @param k the returned neighbors
  * @return std::vector<torch::Tensor> the result tensor for each row of query
  */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);
};

/**
 * @ingroup  CANDY_lib_container
 * @typedef CongestionDropIndexWorkerPtr
 * @brief The class to describe a shared pointer to @ref  CongestionDropIndexWorker

 */
typedef std::shared_ptr<class CANDY::CongestionDropIndexWorker> CongestionDropIndexWorkerPtr;
/**
 * @ingroup  CANDY_lib_container
 * @def newCongestionDropIndexWorker
 * @brief (Macro) To creat a new @ref  CongestionDropIndexWorker shared pointer.
 */
#define newCongestionDropIndexWorker std::make_shared<CANDY::CongestionDropIndexWorker>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
