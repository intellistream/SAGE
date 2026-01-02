/*! \file CLMMCPPAlgo.h*/
//
// Created by tony on 25/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_CLMMCPPALGO_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_CLMMCPPALGO_H_
#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <torch/torch.h>
#include <torch/script.h>
#include <memory>
#include <vector>
#include <CPPAlgos/AbstractCPPAlgo.h>
#include <CL/CLContainer.hpp>
namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class CLMMCPPAlgo CPPAlgos/CLMMCPPAlgo.h
 * @brief The  MM class of c++ algos using opencl
 * @note additionally parameters
 * - clFile, String, default "CL/CLMM"
 */
class CLMMCPPAlgo : public LibAMM::AbstractCPPAlgo {
 protected:
  torch::Tensor clmm(torch::Tensor A, torch::Tensor B);
  torch::Tensor clint8(torch::Tensor A, torch::Tensor B);
  std::string clFile = "CL/CLMM";
  uint64_t clWorkDim = 2;
  TONY_CL_HOST::CLContainerPtr clc = nullptr;
  uint64_t localSize0 = 1, localSize1 = 1;
 public:
  CLMMCPPAlgo() {

  }
  ~CLMMCPPAlgo() {

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
 * @typedef CLMMMatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref CLMMCPPAlgo

 */
typedef std::shared_ptr<class LibAMM::CLMMCPPAlgo> CLMMCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newCLMMCppAlgo
 * @brief (Macro) To creat a new @ref  CLMMCppAlgo shared pointer.
 */
#define newCLMMCPPAlgo std::make_shared<LibAMM::CLMMCPPAlgo>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
