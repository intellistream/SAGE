/*! \file RandomMatrixLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_MATRIXLOADER_RANDOMMATRIXLOADER_H_
#define INTELLISTREAM_INCLUDE_MATRIXLOADER_RANDOMMATRIXLOADER_H_

#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Random The Random generator
 * @{
 */
/**
 * @class RandomMatrixLoader MatrixLoader/RandomMatrixLoader.h
 * @brief The Random class of matrix loader
 * @ingroup LibAMM_MatrixLOADER_Random
 * @note:
 * - Must have a global config by @ref setConfig
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getA and @ref getB (assuming we are benchmarking torch.mm(A,B))
 * @note: require config parameters and default values
 * - "aRow" The rows in matrix A, U64, 100
 * - "aCol" The cols in matrix B, U64, 1000
 * - "bCol" The rows in matrix B, U64, 500
 * - "seed" The seed of inline random generator,U64,114514
 * @note: default name tags
 * "random": @ref RandomMatrixLoader
 */
class RandomMatrixLoader : public AbstractMatrixLoader {
 protected:
  torch::Tensor A, B;
  uint64_t aRow, aCol, bCol, seed;

  /**
   * @brief Inline logic of reading a config file
   * @param cfg the config
   */
  void paraseConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief inline logic of generating A and B
   */
  void generateAB();

 public:
  RandomMatrixLoader() = default;

  ~RandomMatrixLoader() = default;

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
 * @ingroup LibAMM_MatrixLOADER_Random
 * @typedef RandomMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref RandomMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::RandomMatrixLoader> RandomMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Random
 * @def newRandomMatrixLoader
 * @brief (Macro) To creat a new @ref RandomMatrixLoader under shared pointer.
 */
#define newRandomMatrixLoader std::make_shared<LibAMM::RandomMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_INCLUDE_MATRIXLOADER_RANDOMMATRIXLOADER_H_
