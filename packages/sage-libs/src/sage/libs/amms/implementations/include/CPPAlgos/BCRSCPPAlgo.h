/*! \file BCRSCPPAlgo.h*/
//
// Created by haolan on 5/29/23.
//

#ifndef INTELLISTREAM_BCRSCPPALGO_H
#define INTELLISTREAM_BCRSCPPALGO_H

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class BCRSCPPAlgo CPPAlgos/BCRSCPPAlgo.h
 * @brief The Bernoulli column row sampling (BCRS) class of c++ algos
 */
class BCRSCPPAlgo : public LibAMM::AbstractCPPAlgo {
 public:
  BCRSCPPAlgo() {

  }

  ~BCRSCPPAlgo() {

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
 * @brief The class to describe a shared pointer to @ref BCRSCppAlgo

 */
typedef std::shared_ptr<class LibAMM::BCRSCPPAlgo> BCRSCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newBCRSCppAlgo
 * @brief (Macro) To creat a new @ref  BCRSCppAlgounder shared pointer.
 */
#define newBCRSCPPAlgo std::make_shared<LibAMM::BCRSCPPAlgo>
}
/**
 * @}
 */
#endif //INTELLISTREAM_BCRSCPPALGO_H
