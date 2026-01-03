/*! \file OnlineIVFL2HIndex*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_ONLINEIVFL2HINDEX_H_
#define CANDY_INCLUDE_CANDY_ONLINEIVFL2HINDEX_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <faiss/IndexFlat.h>
#include <AbstractIndex.h>
#include <FlatIndex.h>
#include <OnlineIVFLSHIndex.h>
#include <OnlinePQIndex/IVFTensorEncodingList.h>
#include <faiss/VectorTransform.h>
#include <HashingModels/MLPHashingModel.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_bottom The main body and interfaces of library function
 * @{
 */
/**
 * @class OnlineIVFL2HIndex CANDY/OnlineIVFL2HIndex.h
 * @brief A L2H (learning 2 hash) indexing, using 2-tier IVF List to manage buckets. The base tier is hamming encoding, implemented under list,
 * the top tier is sampled summarization of hamming encoding, implemented under vector (faster access, harder to change, but less representative).
 * The L2H function is using ML to approximate spectral hashing principles (NIPS 2008)
 * @note currently single thread
 * @note using hamming L2H function defined in faiss
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - candidateTimes, the times of k to determine minimum candidates, default 1 ,I64
 * - numberOfBuckets, the number of first titer buckets, default 1, I64, suggest 2^n
 * - encodeLen, the length of L2H encoding, in bytes, default 1, I64
 * - metricType, the type of AKNN metric, default L2, String
 * - buildingSamples, the number of samples for building internal ML model during initial loading, default -1, I64
 * - buildingANNK, the ANNK for labeling data as input, default 10, I64
 * @note machine learning extra configs
 * - cudaBuild whether or not use cuda to build model, I64, default 0
 * - learningRate the learning rate for training, Double, default 0.1
 * - hiddenLayerDim the dimension of hidden layer, I64, default the same as output layer
 * - MLTrainBatchSize the batch size of ML training, I64, default 128
 * - MLTrainMargin the margin value in regulating variance used in training, Double, default 2.0
 * - MLTrainEpochs the number of epochs in training, I64, default 30
 * - positiveSampleRatio the ratio of positive samples during self-supervised learning, Double, default 0.1 (should be 0~1)
 */
class OnlineIVFL2HIndex : public OnlineIVFLSHIndex {
 protected:
  MLPHashingModelPtr myMLModel = nullptr;
  virtual torch::Tensor randomProjection(torch::Tensor &a);
  int64_t buildingSamples = -1, buildingANNK = 10;
  FlatIndex trainIndex;
  double positiveSampleRatio = 0.1;
  /**
   * @brief self-supervised learning on data, including automatic labeling
   * @param t the input tensor
   */
  void trainModelWithData(torch::Tensor &t);
 public:
  OnlineIVFL2HIndex() {

  }

  ~OnlineIVFL2HIndex() {

  }
  /**
   * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
   * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
   * @param t the tensor, some index need to be single row
   * @return bool whether the loading is successful
   */
  virtual bool loadInitialTensor(torch::Tensor &t);

  /**
   * @brief set the index-specific config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);
  /**
  * @brief load the initial tensors and query distributions of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the data tensor
  * @param query the example query tensor
  * @return bool whether the loading is successful
  */
  virtual bool loadInitialTensorAndQueryDistribution(torch::Tensor &t, torch::Tensor &query);

};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef OnlineIVFL2HIndexPtr
 * @brief The class to describe a shared pointer to @ref  OnlineIVFL2HIndex

 */
typedef std::shared_ptr<class CANDY::OnlineIVFL2HIndex> OnlineIVFL2HIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newOnlineIVFL2HIndex
 * @brief (Macro) To creat a new @ref  OnlineIVFL2HIndex shared pointer.
 */
#define newOnlineIVFL2HIndex std::make_shared<CANDY::OnlineIVFL2HIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
