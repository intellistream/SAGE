/*! \file RandomDataLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef CANDY_INCLUDE_DATALOADER_RandomDataLoader_H_
#define CANDY_INCLUDE_DATALOADER_RandomDataLoader_H_

#include <Utils/ConfigMap.hpp>
#include <Utils/IntelliTensorOP.hpp>
#include <assert.h>
//#include <torch/torch.h>
#include <memory>
#include <DataLoader/AbstractDataLoader.h>
namespace CANDY {
/**
 * @ingroup CANDY_DataLOADER
 * @{
 */
/**
 * @ingroup CANDY_DataLOADER_Random The Random dataloader
 * @{
 */
/**
 * @class RandomDataLoader DataLoader/RandomDataLoader.h
 * @brief The class of ranom data loader,
 * @ingroup CANDY_DataLOADER
 * @note:
 * - Must have a global config by @ref setConfig
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getData to get the raw data
* - call  @ref getQuery to get the query
* @note parameters of config
* - vecDim, the dimension of vectors, default 768, I64
* - vecVolume, the volume of vectors, default 1000, I64
* - driftPosition, the position of starting some 'concept drift', default 0 (no drift), I64
 * - driftOffset, the offset value of concept drift, default 0.5, Double
 * - queryNoiseFraction, the fraction of noise in query, default 0, allow 0~1, Double
* - querySize, the size of query, default 10, I64
* - seed, the random seed, default 7758258, I64
*  @note: default name tags
 * "random": @ref RandomDataLoader
 */
class RandomDataLoader : public AbstractDataLoader {
 protected:
  torch::Tensor A, B;
  int64_t vecDim, vecVolume, querySize, seed;
  int64_t driftPosition;
  double driftOffset, queryNoiseFraction;
 public:
  RandomDataLoader() = default;

  ~RandomDataLoader() = default;

  /**
     * @brief Set the GLOBAL config map related to this loader
     * @param cfg The config map
      * @return bool whether the config is successfully set
      * @note
     */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief get the data tensor
   * @return the generated data tensor
   */
  virtual torch::Tensor getData();

  /**
  * @brief get the query tensor
  * @return the generated query tensor
  */
  virtual torch::Tensor getQuery();
};

/**
 * @ingroup CANDY_MatrixLOADER_Random
 * @typedef RandomDataLoaderPtr
 * @brief The class to describe a shared pointer to @ref RandomDataLoader

 */
typedef std::shared_ptr<class CANDY::RandomDataLoader> RandomDataLoaderPtr;
/**
 * @ingroup CANDY_MatrixLOADER_Random
 * @def newRandomDataLoader
 * @brief (Macro) To creat a new @ref RandomDataLoader under shared pointer.
 */
#define newRandomDataLoader std::make_shared<CANDY::RandomDataLoader>
/**
 * @}
 */
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_MATRIXLOADER_RandomDataLoader_H_
