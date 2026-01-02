/*! \file YinYangGraphSimpleIndex.h*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_YINYANGGRAPHSIMPLEINDEX_H_
#define CANDY_INCLUDE_CANDY_YINYANGGRAPHSIMPLEINDEX_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <faiss/IndexFlat.h>
#include <CANDY/AbstractIndex.h>
#include <CANDY/YinYangGraphIndex/YinYangGraph.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_bottom The main body and interfaces of library function
 * @{
 */
/**
 * @class YinYangGraphSimpleIndex CANDY/YinYangGraphSimpleIndex.h
 * @brief The class of indexing using a  simpe yinyang graph,there is no LSH
 * search is only within the linked yinyanggraph
 * @todo implement the delete and revise later
 * @note currently single thread
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - maxConnection, the max number of connections in the yinyang graph (for yang vertex of data), default 256, I64
 * - candidateTimes, the times of k to determine minimum candidates, default 1 ,I64
 * - metricType, the type of AKNN metric, default L2, String
 */
class YinYangGraphSimpleIndex : public AbstractIndex {
 protected:
  INTELLI::ConfigMapPtr myCfg = nullptr;
  std::vector<YinYangVertexMap> vertexMapGe1Vec;
  //CANDY::YinYangGraph yyg;
  // torch::Tensor dbTensor;
  int64_t vecDim = 0;
  int64_t maxConnection = 0;
  int64_t candidateTimes = 1;
  YinYangVertexPtr startPoint = nullptr;
  //initialVolume = 1000, expandStep = 100;
  /**
   * @brief insert a tensor
   * @param t the tensor, single row
   * @return bool whether the insertion is successful
   */
  virtual bool insertSingleRowTensor(torch::Tensor &t);
 public:
  YinYangGraphSimpleIndex() {

  }

  ~YinYangGraphSimpleIndex() {

  }
  /**
   * @brief set the index-specific config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief insert a tensor
   * @param t the tensor, accept multiple rows
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensor(torch::Tensor &t);

  /**
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);

};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef YinYangGraphSimpleIndexPtr
 * @brief The class to describe a shared pointer to @ref  YinYangGraphSimpleIndex

 */
typedef std::shared_ptr<class CANDY::YinYangGraphSimpleIndex> YinYangGraphSimpleIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newYinYangGraphSimpleIndex
 * @brief (Macro) To creat a new @ref  YinYangGraphSimpleIndex shared pointer.
 */
#define newYinYangGraphSimpleIndex std::make_shared<CANDY::YinYangGraphSimpleIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
