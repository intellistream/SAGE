/*! \file CRSCPPAlgo.h*/
//
// Created by tony on 25/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_CRSCppAlgo_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_CRSCppAlgo_H_

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class CRSCPPAlgo CPPAlgos/CRSCPPAlgo.h
 * @brief The column row sampling (CRS) class of c++ algos
 *
 */
class CRSCPPAlgo : public LibAMM::AbstractCPPAlgo {
 public:
  CRSCPPAlgo() {

  }

  ~CRSCPPAlgo() {

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
 * @brief The class to describe a shared pointer to @ref CRSCppAlgo

 */
typedef std::shared_ptr<class LibAMM::CRSCPPAlgo> CRSCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newCRSCppAlgo
 * @brief (Macro) To creat a new @ref  CRSCppAlgounder shared pointer.
 */
#define newCRSCPPAlgo std::make_shared<LibAMM::CRSCPPAlgo>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_CRSCppAlgo_H_
