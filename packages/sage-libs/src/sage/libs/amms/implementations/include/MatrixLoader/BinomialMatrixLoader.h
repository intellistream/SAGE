//
// Created by haolan on 6/5/23.
//

#ifndef INTELLISTREAM_BINOMIALMATRIXLOADER_H
#define INTELLISTREAM_BINOMIALMATRIXLOADER_H

#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Binomial The Binomial generator
 * @{
 */
/**
 * @class BinomialMatrixLoader MatrixLoader/BinomialMatrixLoader.h
 * @brief The Binomial class of matrix loader
 * @ingroup LibAMM_MatrixLOADER_Binomial
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
 * - "trials" parameters of binomial distribution, U64, 10
 * - "probability" parameters of binomial distribution, Double, 0.5
 * @note: default name tags
 * "random": @ref BinomialMatrixLoader
 */
class BinomialMatrixLoader : public AbstractMatrixLoader {
 protected:
  torch::Tensor A, B;
  uint64_t aRow, aCol, bCol, seed, trials;
  double probability;

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
  BinomialMatrixLoader() = default;

  ~BinomialMatrixLoader() = default;

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
 * @ingroup LibAMM_MatrixLOADER_Binomial
 * @typedef BinomialMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref BinomialMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::BinomialMatrixLoader> BinomialMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Binomial
 * @def newBinomialMatrixLoader
 * @brief (Macro) To creat a new @ref BinomialMatrixLoader under shared pointer.
 */
#define newBinomialMatrixLoader std::make_shared<LibAMM::BinomialMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_BINOMIALMATRIXLOADER_H
