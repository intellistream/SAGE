/*! \file ZipfMatrixLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_MATRIXLOADER_ZIPFMATRIXLOADER_H_
#define INTELLISTREAM_INCLUDE_MATRIXLOADER_ZIPFMATRIXLOADER_H_

#include <MatrixLoader/AbstractMatrixLoader.h>
#include <vector>
namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Zipf The Zipf generator
 * @{
 */
/**
 * @class ZipfMatrixLoader MatrixLoader/ZipfMatrixLoader.h
 * @brief The Zipf class of matrix loader
 * @ingroup LibAMM_MatrixLOADER_Zipf
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
 * - "zipfAlphaA" The zipf factor for A, Double, 0-highly skewed value. 1- uniform dist.
 * - "zipfAlphaB" The zipf factor for B, Double, 0-highly skewed value. 1- uniform dist.
 * - "randA" whether let A a random matrix. U64 0
 * - "randB" whether let B a random matrix. U64 0
 * @note: default name tags
 * "random": @ref ZipfMatrixLoader
 */
class ZipfMatrixLoader : public AbstractMatrixLoader {
 protected:
  torch::Tensor A, B;
  uint64_t aRow, aCol, bCol, seed, randA,randB;
  double zipfAlphaA,zipfAlphaB;
  /**
   * @brief Inline logic of reading a config file
   * @param cfg the config
   */
  void paraseConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief inline logic of generating A and B
   */
  void generateAB();
  torch::Tensor generateZipfDistribution(int64_t rows, int64_t cols,double alpha);
 public:
  ZipfMatrixLoader() = default;

  ~ZipfMatrixLoader() = default;

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
 * @ingroup LibAMM_MatrixLOADER_Zipf
 * @typedef ZipfMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref ZipfMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::ZipfMatrixLoader> ZipfMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Zipf
 * @def newZipfMatrixLoader
 * @brief (Macro) To creat a new @ref ZipfMatrixLoader under shared pointer.
 */
#define newZipfMatrixLoader std::make_shared<LibAMM::ZipfMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_INCLUDE_MATRIXLOADER_RANDOMMATRIXLOADER_H_
