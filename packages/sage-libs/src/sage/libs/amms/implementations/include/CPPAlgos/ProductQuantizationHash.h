/*! \file ProductQuantizationHash.h*/
//
// Created by haolan on 25/6/23.
//

#ifndef INTELLISTREAM_PRODUCTQUANTIZATIONHASH_H
#define INTELLISTREAM_PRODUCTQUANTIZATIONHASH_H
#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class ProductQuantizationHash CPPAlgos/ProductQuantizationHash.h
 * @brief The Product Quantization AMM class of c++ algos, using hash function to find matching prototypes
 *
 */
  class ProductQuantizationHash : public LibAMM::AbstractCPPAlgo {

  protected:
      string prototypesLoadPath;
      string hashLoadPath;
      int64_t C;

  public:
      ProductQuantizationHash() {

  }

  ~ProductQuantizationHash() {

  }

  /**
   * @brief set the alo-specfic config related to one algorithm
   * @param prototypesLoadPath where to load prototypes
   * @param hashLoadPath where to load hash
   */
  virtual void setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief the virtual function provided for outside callers, rewrite in children classes
   * @param A the A matrix
   * @param B the B matrix
   * @param sketchSize the size of sketc or sampling
   * @return the output c matrix
   */
  virtual torch::Tensor amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize);

};

/**
 * @ingroup LibAMM_CppAlgos
 * @typedef AbstractMatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref ProductQuantizationHashAlgo

 */
typedef std::shared_ptr<class LibAMM::ProductQuantizationHash> ProductQuantizationHashPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newProductQuantizationHashAlgo
 * @brief (Macro) To creat a new @ref  ProductQuantizationHashAlgounder shared pointer.
 */
#define newProductQuantizationHashAlgo std::make_shared<LibAMM::ProductQuantizationHash>
}
/**
 * @}
 */
#endif //INTELLISTREAM_PRODUCTQUANTIZATIONHASH_H
