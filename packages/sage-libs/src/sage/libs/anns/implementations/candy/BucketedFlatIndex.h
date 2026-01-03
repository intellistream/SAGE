/*! \file BucketedFlatIndex.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_BucketedFlatIndex_H_
#define CANDY_INCLUDE_CANDY_BucketedFlatIndex_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <faiss/IndexFlat.h>
#include <AbstractIndex.h>
#include <FlatIndex.h>
#include <HashingModels/MLPBucketIdxModel.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_bottom The main body and interfaces of library function
 * @{
 */
/**
 * @class BucketedFlatIndex CANDY/BucketedFlatIndex.h
 * @brief The class of splitting similar vectors into fixed number of buckets, each bucket is managed by @ref FlatIndex
 * @note currently single thread
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - initialVolume, the initial volume of inline database tensor, default 1000, I64
 * - expandStep, the step of expanding inline database, default 100, I64
 * - numberOfBuckets, the number of titer buckets, default 1, I64, suggest 2^n
 * - bucketMode, the mode of assigning buckets, default 'mean', String, allow the following with its own parameters
    * - 'mean': the bucket is assigned by uniform quantization of the mean, the quantization step is assigned by numberOfBuckets require following parameters
        * - quantizationMax the max value used for quantization, default 1, Double
        * - quantizationMin the min value used for quantization, default -1, Double
    * - 'LSH: the bucket is assigned by LSH, and raw LSH encoding will be aggregated according to numberOfBuckets
        * - encodeLen, the length of LSH encoding, in bytes, default 1, I64
        * - metricType, the type of AKNN metric, default L2, String
        * - lshMatrixType, the type of lsh matrix, default gaussian, String
            * - gaussian means a N(0,1) LSH matrix
            * - random means a random matrix where each value ranges from -0.5~0.5
     * - 'ML': the bucket is assigned by maching learning to generate bucket indicies
        * - encodeLen, the length of LSH encoding, in bytes, default 1, I64
        * - metricType, the type of AKNN metric, default L2, String
        * - cudaBuild whether or not use cuda to build model, I64, default 0
        * - learningRate the learning rate for training, Double, default 0.01
        * - hiddenLayerDim the dimension of hidden layer, I64, default the same as output layer
        * - MLTrainBatchSize the batch size of ML training, I64, default 64
        * - MLTrainMargin the margin value used in training, Double, default 2*0.1
        * - MLTrainEpochs the number of epochs in training, I64, default 10
        *
 */
class BucketedFlatIndex : public AbstractIndex {
 protected:
  INTELLI::ConfigMapPtr myCfg = nullptr;
  torch::Tensor dbTensor;
  int64_t vecDim = 0, initialVolume = 1000, expandStep = 100;
  int64_t numberOfBuckets = 1;
  int64_t buildingSamples = -1, buildingANNK = 10;
  int64_t bucketModeNumber;
  int64_t bucketsLog2 = 0;
  std::vector<FlatIndexPtr> buckets;
  double quantizationMax, quantizationMin;
  int64_t encodeLen;
  torch::Tensor rotationMatrix;
  uint64_t encodeSingleRowMean(torch::Tensor &tensor);
  uint64_t encodeSingleRowLsh(torch::Tensor &tensor);
  std::vector<uint64_t> encodeMultiRows(torch::Tensor &tensor);
  MLPBucketIdxModelPtr myMLModel = nullptr;
  /**
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow only single rows
   * @param bkt the bucket number which fits best
   * @param k the returned neighbors
   * @return the result tensor
   */
  torch::Tensor searchSingleRow(torch::Tensor &q, uint64_t bkt, int64_t k);
 public:
  BucketedFlatIndex() {

  }

  ~BucketedFlatIndex() {

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
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);
  /**
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the tensor, some index need to be single row
  * @return bool whether the loading is successful
  */
  virtual bool loadInitialTensor(torch::Tensor &t);

};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef BucketedFlatIndexPtr
 * @brief The class to describe a shared pointer to @ref  BucketedFlatIndex

 */
typedef std::shared_ptr<class CANDY::BucketedFlatIndex> BucketedFlatIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newBucketedFlatIndex
 * @brief (Macro) To creat a new @ref  BucketedFlatIndex shared pointer.
 */
#define newBucketedFlatIndex std::make_shared<CANDY::BucketedFlatIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
