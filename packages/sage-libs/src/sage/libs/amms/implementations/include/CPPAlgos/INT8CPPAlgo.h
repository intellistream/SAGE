/*! \file INT8CPPAlgo.h*/
//
// Created by tony on 25/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_INT8CPPALGO_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_INT8CPPALGO_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <torch/torch.h>
#include <torch/script.h>
#include <memory>
#include <vector>
#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class INT8CPPAlgo CPPAlgos/INT8CPPAlgo.h
 * @brief The INT8 MM class of c++ algos
 * @warning This function disables all additional optimization by libtorch, as it has different, and not fair SIMD/cache optimization
 * over FP32/INT16/INT8 on cpu, which is hard to compare
 * @note additionally parameters
 * - fpMode, String, default FP32, can also use INT8 or INT16
 */
class INT8CPPAlgo : public LibAMM::AbstractCPPAlgo {
 protected:
  /**
  * @brief the inline amm under nested loop fp32
  * @param A the A matrix
  * @param B the B matrix
  * @return the output c matrix
  */
  torch::Tensor fp32amm(torch::Tensor A, torch::Tensor B);

  /**
  * @brief the inline amm under nested loop fp64
  * @param A the A matrix
  * @param B the B matrix
  * @return the output c matrix
  */
  torch::Tensor fp64amm(torch::Tensor A, torch::Tensor B);

  /**
  * @brief the inline amm under nested loop int8
  * @param A the A matrix
  * @param B the B matrix
  * @return the output c matrix
  */
  torch::Tensor int8amm(torch::Tensor A, torch::Tensor B);

  /**
  * @brief the inline amm under nested loop int4
  * @param A the A matrix
  * @param B the B matrix
  * @return the output c matrix
  */
  torch::Tensor int4amm(torch::Tensor A, torch::Tensor B);

  /**
 * @brief the inline amm under nested loop int16
 * @param A the A matrix
 * @param B the B matrix
 * @return the output c matrix
 */
  torch::Tensor int16amm(torch::Tensor A, torch::Tensor B);

  std::string fpMode = "FP32";
 public:
  INT8CPPAlgo() {

  }

  ~INT8CPPAlgo() {

  }

  /**
   * @brief the virtual function provided for outside callers, rewrite in children classes
   * @param A the A matrix
   * @param B the B matrix
   * @param sketchSize the size of sketc or sampling
   * @return the output c matrix
   */
  virtual torch::Tensor amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize);

  /**
 * @brief set the alo-specfic config related to one algorithm
 */
  virtual void setConfig(INTELLI::ConfigMapPtr cfg);
};

/**
 * @ingroup LibAMM_CppAlgos
 * @typedef INT8MatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref INT8CPPAlgo

 */
typedef std::shared_ptr<class LibAMM::INT8CPPAlgo> INT8CPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newINT8CppAlgo
 * @brief (Macro) To creat a new @ref  INT8CppAlgo shared pointer.
 */
#define newINT8CPPAlgo std::make_shared<LibAMM::INT8CPPAlgo>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
