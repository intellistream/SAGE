/*! \file ExpFamilyDataLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef CANDY_INCLUDE_DATALOADER_ExpFamilyDataLoader_H_
#define CANDY_INCLUDE_DATALOADER_ExpFamilyDataLoader_H_

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
 * @ingroup CANDY_DataLOADER_ExpFamily The ExpFamily dataloader
 * @{
 */
/**
 * @class ExpFamilyDataLoader DataLoader/ExpFamilyDataLoader.h
 * @brief The class to load data from exponential family, i.e., poisson, gaussian, exponential and beta
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
* - parameterBetaA, the a parameter in beta distribution, default 2.0, double
* - parameterBetaB, the b parameter in beta distribution, default 2.0, double
* - normalizeTensor, whether or not additionally normalize the tensors in L2, 0 (no), I64
 * - driftOffset, the offset value of concept drift, default 0.5, Double
 * - queryNoiseFraction, the fraction of noise in query, default 0, allow 0~1, Double
* - querySize, the size of query, default 10, I64
* - manualChangeDistribution, open this to manually change the distribution, default 0, I64
* - distributionOverwrite, the string indicator to manually overwrite the distribution tag, default exponential, String, can be any one of
 * - poisson
 * - gaussian
 * - exp
 * - beta
* - seed, the ExpFamily seed, default 7758258, I64
*  @note: default name tags
 * "ExpFamily": @ref ExpFamilyDataLoader
 */
class ExpFamilyDataLoader : public AbstractDataLoader {
 protected:
  torch::Tensor A, B;
  int64_t vecDim, vecVolume, querySize, seed;
  int64_t driftPosition;
  int64_t manualChangeDistribution;
  std::string distributionOverwrite;
  double driftOffset, queryNoiseFraction;
  int64_t normalizeTensor;
  double parameterBetaA, parameterBetaB;

  torch::Tensor generateExp();
  torch::Tensor generateGaussian();
  torch::Tensor generateBinomial();
  torch::Tensor generatePoisson();

  torch::Tensor generateBeta();
  torch::Tensor generateData();
 public:
  ExpFamilyDataLoader() = default;

  ~ExpFamilyDataLoader() = default;
  /**
    * @brief To hijack some configurations inline
    * @param cfg The config map
     * @return bool whether the config is successfully set
     * @note
    */
  virtual bool hijackConfig(INTELLI::ConfigMapPtr cfg);
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
 * @ingroup CANDY_MatrixLOADER_ExpFamily
 * @typedef ExpFamilyDataLoaderPtr
 * @brief The class to describe a shared pointer to @ref ExpFamilyDataLoader

 */
typedef std::shared_ptr<class CANDY::ExpFamilyDataLoader> ExpFamilyDataLoaderPtr;
/**
 * @ingroup CANDY_MatrixLOADER_ExpFamily
 * @def newExpFamilyDataLoader
 * @brief (Macro) To creat a new @ref ExpFamilyDataLoader under shared pointer.
 */
#define newExpFamilyDataLoader std::make_shared<CANDY::ExpFamilyDataLoader>
/**
 * @}
 */
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_MATRIXLOADER_ExpFamilyDataLoader_H_
