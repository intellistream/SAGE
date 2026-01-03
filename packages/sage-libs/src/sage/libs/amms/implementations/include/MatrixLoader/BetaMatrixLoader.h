//
// Created by haolan on 6/6/23.
//

#ifndef INTELLISTREAM_BETAMATRIXLOADER_H
#define INTELLISTREAM_BETAMATRIXLOADER_H

#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Beta The Beta generator
 * @{
 */
/**
 * @class BetaMatrixLoader MatrixLoader/BetaMatrixLoader.h
 * @brief The Beta class of matrix loader
 * @ingroup LibAMM_MatrixLOADER_Beta
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
 * - "a" parameters of beta distribution, Double, 2.0
 * - "b" parameters of beta distribution, Double, 2.0
 * @note: default name tags
 * "random": @ref BetaMatrixLoader
 */
class BetaMatrixLoader : public AbstractMatrixLoader {
 protected:
  torch::Tensor A, B;
  uint64_t aRow, aCol, bCol, seed;
  double a, b;

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
  BetaMatrixLoader() = default;

  ~BetaMatrixLoader() = default;

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
 * @ingroup LibAMM_MatrixLOADER_Beta
 * @typedef BetaMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref BetaMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::BetaMatrixLoader> BetaMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Beta
 * @def newBetaMatrixLoader
 * @brief (Macro) To creat a new @ref BetaMatrixLoader under shared pointer.
 */
#define newBetaMatrixLoader std::make_shared<LibAMM::BetaMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_BETAMATRIXLOADER_H
