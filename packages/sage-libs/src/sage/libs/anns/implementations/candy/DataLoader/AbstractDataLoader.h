/*! \file AbstractDataLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef CANDY_INCLUDE_DATALOADER_AbstractDataLoader_H_
#define CANDY_INCLUDE_DATALOADER_AbstractDataLoader_H_

#include <Utils/ConfigMap.hpp>
#include <Utils/IntelliTensorOP.hpp>
#include <assert.h>
//#include <torch/torch.h>
#include <memory>

namespace CANDY {
/**
 * @ingroup CANDY_DataLOADER
 * @{
 */
/**
 * @ingroup CANDY_DataLOADER_abstract The abstract template
 * @{
 */
/**
 * @class AbstractDataLoader DataLoader/AbstractDataLoader.h
 * @ingroup CANDY_DataLOADER
 * @brief The abstract class of data loader, parent for all loaders
 * @ingroup CANDY_MatrixLOADER_abstract
 * @note:
 * - Must have a global config by @ref setConfig
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getData to get the raw data
* - call  @ref getQuery to get the query
 */
class AbstractDataLoader {
 public:
  AbstractDataLoader() = default;

  ~AbstractDataLoader() = default;
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
   * @brief get the data tensor at specific offset
   * @note implement and use this when the whole data tensor does not fit into main memory
   * @return the generated data tensor
   */
  virtual torch::Tensor getDataAt(int64_t startPos, int64_t endPos);
  /**
  * @brief get the query tensor
  * @return the generated query tensor
  */
  virtual torch::Tensor getQuery();

  /**
   * @brief get the data tensor at specific offset
   * @note implement and use this when the whole data tensor does not fit into main memory
   * @return the generated data tensor
   */
  virtual torch::Tensor getQueryAt(int64_t startPos, int64_t endPos);
  /**
   * @brief get the dimension of data
   * @return the dimension
   */
  virtual int64_t getDimension();
  /**
   * @brief get the number of rows of data
   * @return the rows
   */
  virtual int64_t size();
};

/**
 * @ingroup CANDY_MatrixLOADER_abstract
 * @typedef AbstractDataLoaderPtr
 * @brief The class to describe a shared pointer to @ref AbstractDataLoader

 */
typedef std::shared_ptr<class CANDY::AbstractDataLoader> AbstractDataLoaderPtr;
/**
 * @ingroup CANDY_MatrixLOADER_abstract
 * @def newAbstractDataLoader
 * @brief (Macro) To creat a new @ref AbstractDataLoader under shared pointer.
 */
#define newAbstractDataLoader std::make_shared<CANDY::AbstractDataLoader>
/**
 * @}
 */
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_MATRIXLOADER_AbstractDataLoader_H_
