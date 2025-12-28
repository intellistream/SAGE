/*! \file ZipfDataLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef CANDY_INCLUDE_DATALOADER_ZipfDataLoader_H_
#define CANDY_INCLUDE_DATALOADER_ZipfDataLoader_H_

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
 * @ingroup CANDY_DataLOADER_Zipf The Zipf dataloader
 * @{
 */
/**
 * @class ZipfDataLoader DataLoader/ZipfDataLoader.h
 * @brief The class to load zipf data
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
* - normalizeTensor, whether or not normalize the tensors in L2, 1 (yes), I64
* - "zipfAlpha" The zipf factor for, Double, 0-highly skewed value. 1- uniform dist.
* - driftPosition, the position of starting some 'concept drift', default 0 (no drift), I64
 * - driftOffset, the offset value of concept drift, default 0.5, Double
 * - queryNoiseFraction, the fraction of noise in query, default 0, allow 0~1, Double
* - querySize, the size of query, default 10, I64
* - seed, the Zipf seed, default 7758258, I64
*  @note: default name tags
 * "Zipf": @ref ZipfDataLoader
 */
class ZipfDataLoader : public AbstractDataLoader {
 protected:
  torch::Tensor A, B;
  int64_t vecDim, vecVolume, querySize, seed;
  int64_t driftPosition;
  double driftOffset, queryNoiseFraction;
  double zipfAlpha;
  torch::Tensor generateZipfDistribution(int64_t n, int64_t m, double alpha);
 public:
  ZipfDataLoader() = default;

  ~ZipfDataLoader() = default;

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
 * @ingroup CANDY_MatrixLOADER_Zipf
 * @typedef ZipfDataLoaderPtr
 * @brief The class to describe a shared pointer to @ref ZipfDataLoader

 */
typedef std::shared_ptr<class CANDY::ZipfDataLoader> ZipfDataLoaderPtr;
/**
 * @ingroup CANDY_MatrixLOADER_Zipf
 * @def newZipfDataLoader
 * @brief (Macro) To creat a new @ref ZipfDataLoader under shared pointer.
 */
#define newZipfDataLoader std::make_shared<CANDY::ZipfDataLoader>
/**
 * @}
 */
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_MATRIXLOADER_ZipfDataLoader_H_
