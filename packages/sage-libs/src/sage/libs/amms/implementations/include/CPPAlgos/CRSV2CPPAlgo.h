/*! \file CRSV2CPPAlgo.h*/
//
// Created by haolan on 5/26/23.
//

#ifndef INTELLISTREAM_CRSV2CPPALGO_H
#define INTELLISTREAM_CRSV2CPPALGO_H

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class CRSV2CPPAlgo CPPAlgos/CRSV2CPPAlgo.h
 * @brief The column row sampling (CRS) class of c++ algos, a second implementation
 *
 */
class CRSV2CPPAlgo : public LibAMM::AbstractCPPAlgo {
 public:
  CRSV2CPPAlgo() {

  }

  ~CRSV2CPPAlgo() {

  }

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
 * @brief The class to describe a shared pointer to @ref CRSV2CppAlgo

 */
typedef std::shared_ptr<class LibAMM::CRSV2CPPAlgo> CRSV2CPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newCRSV2CppAlgo
 * @brief (Macro) To creat a new @ref  CRSV2CppAlgounder shared pointer.
 */
#define newCRSV2CPPAlgo std::make_shared<LibAMM::CRSV2CPPAlgo>
}
/**
 * @}
 */
#endif //INTELLISTREAM_CRSV2CPPALGO_H
