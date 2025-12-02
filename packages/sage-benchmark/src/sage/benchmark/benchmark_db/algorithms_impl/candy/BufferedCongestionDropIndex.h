/*! \file BufferedCongestionDropIndex.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_BufferedCongestionDropIndex_H_
#define CANDY_INCLUDE_CANDY_BufferedCongestionDropIndex_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <AbstractIndex.h>
#include <CongestionDropIndex.h>
#include <BucketedFlatIndex.h>
#include <stdint.h>
#include <vector>
#include <stddef.h>
#include <stdlib.h>
#include <time.h>
#include <random>
#include <cmath>
#include <iostream>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_container
 * @{
 */
/**
 * @class BufferedCongestionDropIndex CANDY/BufferedCongestionDropIndex.h
 * @brief Similar to @ref CongestionDropIndex, but will try to place some of the online data into an ingestion-efficient buffer, the buffer is implemented under @ref BucketedFlatIndex
 * More detailed description with an image:
 * \image latex BufferedCongestionDrop.pdf "An overview of BufferedCongestionDropIndex"
 * under @ref BucketedFlatIndex
 * @note The current decision of where to put data is just by probability
 * @note parameters
 *  - vecDim, the dimension of vectors, default 768, I64
 *  - bufferProbability, the probability of ingesting data into buffer, default 0.5, Double
 *  - maxDataPiece, the max piece of one data throwing into @ref CongestionDropIndex or @ref BucketedFlatIndex, default -1 (full piece for each insert), I64
 * @note special parameters (For configuring the inside @ref CongestionDropIndex)
 *  - congestionDropWorker_algoTag The algo tag of this worker, String, default flat
 *  - congestionDropWorker_queueSize The input queue size of this worker, I64, default 10
 *  - parallelWorks The number of parallel workers, I64, default 1 (set this to less than 0 will use max hardware_concurrency);
 *  - fineGrainedParallelInsert, whether or not conduct the insert in an extremely fine-grained way, i.e., per-row, I64, default 0
 *  - congestionDrop, whether or not drop the data when congestion occurs, I64, default 1
 *  - sharedBuild whether let all sharding using shared build, 1, I64
 *  - singleWorkerOpt whether optimize the searching under single worker, 1 I64
 * @note special parameters (For configuring the inside @ref BucketedFlatIndex)
 * - buffer_initialVolume, the initial volume of inline database tensor, default 1000, I64
 * - buffer_expandStep, the step of expanding inline database, default 100, I64
 * - buffer_numberOfBuckets, the number of titer buckets, default 1, I64, suggest 2^n
 * - buffer_bucketMode, the mode of assigning buckets, default 'mean', String, allow the following with its own parameters
    * - 'mean': the bucket is assigned by uniform quantization of the mean, the quantization step is assigned by numberOfBuckets require following parameters
        * - buffer_quantizationMax the max value used for quantization, default 1, Double
        * - buffer_quantizationMin the min value used for quantization, default -1, Double
    * - 'LSH': the bucket is assigned by LSH, and raw LSH encoding will be aggregated according to numberOfBuckets
        * - buffer_encodeLen, the length of LSH encoding, in bytes, default 1, I64
        * - buffer_metricType, the type of AKNN metric, default L2, String
        * - buffer_lshMatrixType, the type of lsh matrix, default gaussian, String
            * - gaussian means a N(0,1) LSH matrix
            * - random means a random matrix where each value ranges from -0.5~0.5
 * @warnning
 * Make sure you are using 2D tensors!
 */
class BufferedCongestionDropIndex : public CANDY::AbstractIndex {
 protected:
  std::mt19937_64 randGen;
  BucketedFlatIndexPtr bufferPart = nullptr;
  CongestionDropIndexPtr aknnPart = nullptr;
  std::uniform_real_distribution<double> randDistribution;
  double bufferProbability = 0.5;
  int64_t maxDataPiece = -1;
  int64_t vecDim;
  /**
   * @brief to generate the config map of inside @ref BucketedFlatIndex from the top config
   * @param cfg the top config of this index
   * @return the config for inside  @ref BucketedFlatIndex
   */
  INTELLI::ConfigMapPtr generateBucketedFlatIndexConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief insert a tensor to either bufferPart or aknnPart
   * @param t the tensor, some index need to be single row
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensorInline(torch::Tensor &t);
 public:
  BufferedCongestionDropIndex() {

  }

  ~BufferedCongestionDropIndex() {

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
};

/**
 * @ingroup  CANDY_lib_container
 * @typedef BufferedCongestionDropIndexPtr
 * @brief The class to describe a shared pointer to @ref  BufferedCongestionDropIndex

 */
typedef std::shared_ptr<class CANDY::BufferedCongestionDropIndex> BufferedCongestionDropIndexPtr;
/**
 * @ingroup  CANDY_lib_container
 * @def newBufferedCongestionDropIndex
 * @brief (Macro) To creat a new @ref  BufferedCongestionDropIndex shared pointer.
 */
#define newBufferedCongestionDropIndex std::make_shared<CANDY::BufferedCongestionDropIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
