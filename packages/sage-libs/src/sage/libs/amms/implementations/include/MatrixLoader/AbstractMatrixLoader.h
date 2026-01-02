/*! \file AbstractMatrixLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_MATRIXLOADER_ABSTRACTMATRIXLOADER_H_
#define INTELLISTREAM_INCLUDE_MATRIXLOADER_ABSTRACTMATRIXLOADER_H_

#include <Utils/ConfigMap.hpp>
#include <assert.h>
#include <torch/torch.h>
#include <memory>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_abstract The abstract template
 * @{
 */
/**
 * @class AbstractMatrixLoader MatrixLoader/AbstractMatrixLoader.h
 * @brief The abstract class of matrix loader, parent for all loaders
 * @ingroup LibAMM_MatrixLOADER_abstract
 * @note:
 * - Must have a global config by @ref setConfig
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getA and @ref getB (assuming we are benchmarking torch.mm(A,B))
 */
class AbstractMatrixLoader {
 public:
  AbstractMatrixLoader() = default;

  ~AbstractMatrixLoader() = default;

  /**
     * @brief Set the GLOBAL config map related to this loader
     * @param cfg The config map
      * @return bool whether the config is successfully set
      * @note
     */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief get the A matrix
   * @return the generated A matrix
   */
  virtual torch::Tensor getA();

  /**
  * @brief get the B matrix
  * @return the generated B matrix
  */
  virtual torch::Tensor getB();
};

/**
 * @ingroup LibAMM_MatrixLOADER_abstract
 * @typedef AbstractMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref AbstractMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::AbstractMatrixLoader> AbstractMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_abstract
 * @def newAbstractMatrixLoader
 * @brief (Macro) To creat a new @ref AbstractMatrixLoader under shared pointer.
 */
#define newAbstractMatrixLoader std::make_shared<LibAMM::AbstractMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
} // LibAMM

#endif //INTELLISTREAM_INCLUDE_MATRIXLOADER_ABSTRACTMATRIXLOADER_H_
