/*! \file SparseMatrixLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_MATRIXLOADER_SparseMATRIXLOADER_H_
#define INTELLISTREAM_INCLUDE_MATRIXLOADER_SparseMATRIXLOADER_H_

#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Sparse The Sparse generator
 * @{
 */
/**
 * @class SparseMatrixLoader MatrixLoader/SparseMatrixLoader.h
 * @brief The  matrix loader to generate adjustable sparse matrix with adjust rank reduction
 * @ingroup LibAMM_MatrixLOADER_Sparse
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
 * - "seed" The seed of inline Sparse generator,U64,114514
 * - "aDensity" The density factor of matrix A, Double, 1.0
 * - "bDensity" The density factor of matrix B, Double, 1.0
 * - "aReduce" Reduce some rows of A to be linearly dependent, U64, 0
 * - "bReduce" Reduce some rows of A to be linearly dependent, U64, 0
 * @note: default name tags
 * "sparse": @ref SparseMatrixLoader
 */
class SparseMatrixLoader : public AbstractMatrixLoader {
 protected:
  torch::Tensor A, B;
  uint64_t aRow, aCol, bCol, seed, aReduce, bReduce;
  double aDensity, bDensity;

  /**
   * @brief Inline logic of generate the sparse matrix
   * @param m the rows
   * @param n the cols
   * @param density the density in 0~1
   * @param reduceRows the number of rows to be reduced
   */
  torch::Tensor genSparseMatrix(uint64_t m, uint64_t n, double density, uint64_t reduceRows);

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
  SparseMatrixLoader() = default;

  ~SparseMatrixLoader() = default;

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
 * @ingroup LibAMM_MatrixLOADER_Sparse
 * @typedef SparseMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref SparseMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::SparseMatrixLoader> SparseMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Sparse
 * @def newSparseMatrixLoader
 * @brief (Macro) To creat a new @ref SparseMatrixLoader under shared pointer.
 */
#define newSparseMatrixLoader std::make_shared<LibAMM::SparseMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_INCLUDE_MATRIXLOADER_SparseMATRIXLOADER_H_
