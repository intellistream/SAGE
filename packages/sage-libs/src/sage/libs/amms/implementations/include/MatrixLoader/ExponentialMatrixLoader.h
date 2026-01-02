//
// Created by haolan on 6/5/23.
//

#ifndef INTELLISTREAM_EXPONENTIALMATRIXLOADER_H
#define INTELLISTREAM_EXPONENTIALMATRIXLOADER_H

#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Exponential The Exponential generator
 * @{
 */
/**
 * @class ExponentialMatrixLoader MatrixLoader/ExponentialMatrixLoader.h
 * @brief The Exponential class of matrix loader
 * @ingroup LibAMM_MatrixLOADER_Exponential
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
 * "random": @ref ExponentialMatrixLoader
 */
class ExponentialMatrixLoader : public AbstractMatrixLoader {
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
  ExponentialMatrixLoader() = default;

  ~ExponentialMatrixLoader() = default;

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
 * @ingroup LibAMM_MatrixLOADER_Exponential
 * @typedef ExponentialMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref ExponentialMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::ExponentialMatrixLoader> ExponentialMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Exponential
 * @def newExponentialMatrixLoader
 * @brief (Macro) To creat a new @ref ExponentialMatrixLoader under shared pointer.
 */
#define newExponentialMatrixLoader std::make_shared<LibAMM::ExponentialMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_EXPONENTIALMATRIXLOADER_H
