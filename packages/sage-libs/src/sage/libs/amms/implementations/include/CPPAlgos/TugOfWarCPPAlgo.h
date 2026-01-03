/*! \file TugOfWarCPPAlgo.h*/
//
// Created by luv on 5/30/23.
//

#ifndef INTELLISTREAM_TUGOFWARCPPALGO_H
#define INTELLISTREAM_TUGOFWARCPPALGO_H

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms writtrn in c++
 * @{
 */
/**
 * @class TugOfWarCPPAlgo CPPAlgos/TugOfWarCPPAlgo.h
 * @brief The tug of war class of c++ algoS
 * @note parameters
 * - algoDelta Double, the delta parameter in this algo, default 0.02
 */
class TugOfWarCPPAlgo : public LibAMM::AbstractCPPAlgo {
  double algoDelta = 0.02;

 public:
  TugOfWarCPPAlgo() {

  }

  ~TugOfWarCPPAlgo() {

  }

  /**
 * @brief set the algo-specfic config related to one algorithm
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

 private:
  torch::Tensor generateTugOfWarMatrix(int64_t m, int64_t n);

};

/**
 * @ingroup LibAMM_CppAlgos
 * @typedef AbstractMatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref TugOfWarCppAlgo

 */
typedef std::shared_ptr<class LibAMM::TugOfWarCPPAlgo> TugOfWarCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newTugOfWarCppAlgo
 * @brief (Macro) To creat a new @ref  TugOfWarCppAlgounder shared pointer.
 */
#define newTugOfWarCPPAlgo std::make_shared<LibAMM::TugOfWarCPPAlgo>
}
/**
 * @}
 */
#endif //INTELLISTREAM_TUGOFWARCPPALGO_H
