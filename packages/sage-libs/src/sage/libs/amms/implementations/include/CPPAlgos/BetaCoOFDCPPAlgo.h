/*! \file BetaCoOFDCPPAlgo.h*/
// Created by haolan on 5/30/23.
//

#ifndef INTELLISTREAM_BETACOOFDCPPALGO_H
#define INTELLISTREAM_BETACOOFDCPPALGO_H

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class BetaCoOFDCPPAlgo CPPAlgos/BetaCoOFDCPPAlgo.h
 * @brief The Beta Co-Occurring FD AMM class of c++ algos
 * @note parameters
 * - algoBeta Double, the beta parameters in this algo, default 1.0
 */
class BetaCoOFDCPPAlgo : public LibAMM::AbstractCPPAlgo {
 protected:
  float algoBeta = 1.0;
 public:
  BetaCoOFDCPPAlgo() {

  }

  ~BetaCoOFDCPPAlgo() {

  }

  /**
   * @brief set the alo-specfic config related to one algorithm
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
 * @brief The class to describe a shared pointer to @ref BetaCoOFDCppAlgo

 */
typedef std::shared_ptr<class LibAMM::BetaCoOFDCPPAlgo> BetaCoOFDCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newBetaCoOFDCppAlgo
 * @brief (Macro) To creat a new @ref  BetaCoOFDCppAlgounder shared pointer.
 */
#define newBetaCoOFDCPPAlgo std::make_shared<LibAMM::BetaCoOFDCPPAlgo>
}
/**
 * @}
 */
#endif //INTELLISTREAM_BETACOOFDCPPALGO_H
