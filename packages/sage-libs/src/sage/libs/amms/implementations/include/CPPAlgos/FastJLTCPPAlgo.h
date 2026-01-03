/*! \file FastJLTCPPAlgo.h*/
//
// Created by luv on 6/18/23.
//

#ifndef INTELLISTREAM_FASTFLTCPPALGO_H
#define INTELLISTREAM_FASTJLTCPPALGO_H

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms writtrn in c++
 * @{
 */
/**
 * @class FastJLTCPPAlgo CPPAlgos/FastJLTCPPAlgo.h
 * @brief The tug of war class of c++ algoS
 */
class FastJLTCPPAlgo : public LibAMM::AbstractCPPAlgo {
 public:
  FastJLTCPPAlgo() {

  }

  ~FastJLTCPPAlgo() {

  }

  /**
   * @brief the virtual function provided for outside callers, rewrite in children classes
   * @param A the A matrix
   * @param B the B matrix
   * @param sketchSize the size of sketc or sampling
   * @return the output c matrix
   */
  virtual torch::Tensor amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize);

 private:
};

/**
 * @ingroup LibAMM_CppAlgos
 * @typedef AbstractMatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref FastJLTCppAlgo

 */
typedef std::shared_ptr<class LibAMM::FastJLTCPPAlgo> FastJLTCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newFastJLTCppAlgo
 * @brief (Macro) To creat a new @ref  FastJLTCppAlgounder shared pointer.
 */
#define newFastJLTCPPAlgo std::make_shared<LibAMM::FastJLTCPPAlgo>
}
/**
 * @}
 */
#endif //INTELLISTREAM_FASTJLTCPPALGO_H
