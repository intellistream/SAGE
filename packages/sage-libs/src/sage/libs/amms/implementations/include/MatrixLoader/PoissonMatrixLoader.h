//
// Created by haolan on 6/6/23.
//

#ifndef INTELLISTREAM_POISSONMATRIXLOADER_H
#define INTELLISTREAM_POISSONMATRIXLOADER_H

#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Poisson The Poisson generator
 * @{
 */
/**
 * @class PoissonMatrixLoader MatrixLoader/PoissonMatrixLoader.h
 * @brief The Poisson class of matrix loader
 * @ingroup LibAMM_MatrixLOADER_Poisson
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
 * "random": @ref PoissonMatrixLoader
 */
class PoissonMatrixLoader : public AbstractMatrixLoader {
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
  PoissonMatrixLoader() = default;

  ~PoissonMatrixLoader() = default;

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
 * @ingroup LibAMM_MatrixLOADER_Poisson
 * @typedef PoissonMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref PoissonMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::PoissonMatrixLoader> PoissonMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Poisson
 * @def newPoissonMatrixLoader
 * @brief (Macro) To creat a new @ref PoissonMatrixLoader under shared pointer.
 */
#define newPoissonMatrixLoader std::make_shared<LibAMM::PoissonMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_POISSONMATRIXLOADER_H
