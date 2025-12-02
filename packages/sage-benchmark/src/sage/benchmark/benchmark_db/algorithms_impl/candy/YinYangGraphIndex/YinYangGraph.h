/*! \file YinYangGraph.h*/
//
// Created by tony on 31/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_YINGYANGVERTEXINDEX_YINYANGGRAPH_H_
#define CANDY_INCLUDE_CANDY_YINGYANGVERTEXINDEX_YINYANGGRAPH_H_
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <string>
#include <sstream>
#include <queue>
#include <memory>
#include <map>
namespace CANDY {

class YinYangVertex;
class YinYangVertexMap;
using floatDistanceFunction_t = float (*)(const torch::Tensor &, const torch::Tensor &);
class YinYangGraph_DistanceFunctions {
 public:
  YinYangGraph_DistanceFunctions() {

  }
  ~YinYangGraph_DistanceFunctions() {

  }
  static float L2Distance(const torch::Tensor &tensor1, const torch::Tensor &tensor2) {
    torch::Tensor squaredDiff = torch::pow(tensor1 - tensor2, 2);
    // Sum up the distances and return as float
    float sum = torch::sum(squaredDiff).item<float>();
    return sum;
  }
};
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @typedef YinYangVertexPtr
 * @brief The class to describe a shared pointer to @ref YinYangVertex
 */
typedef std::shared_ptr<CANDY::YinYangVertex> YinYangVertexPtr;
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @def newYinYangVertex
 * @brief (Macro) To creat a new @ref YinYangVertex under shared pointer.
 */
#define  newYinYangVertex make_shared<CANDY::YinYangVertex>
/**
 * @class YinYangVertex CANDY/YinYangIndex/YinYangGraph.h
 * @brief The class of a  YinYangVertex, storing the data in each vertex
 * @note now storing each vertex's neighbors, visited number and level, with a pointer to the vector
 * @note
 *  - yin: means this is a summarizing or bridge tensor, not a really data point
    * - yin vertex will only be used for navigation, not output to result
    * - yin vertex will be less likely to be deleted, completely changed compared with yang
    * - yin vertex can be a summary of multiple tensors
 *  - yang: means the real data point
 */

class YinYangVertex {
 protected :
  std::mutex m_mut;
 public:
  INTELLI::TensorPtr tensorSummary;
  int64_t containedTensors = 0;
  int64_t level = 0;
  int64_t connectedNeighbors = 0;
  int64_t maxConnections = 0;
  bool isYang = false;
  //std::vector<YinYangVertexPtr> neighbors;
  std::map<CANDY::YinYangVertexPtr, CANDY::YinYangVertexPtr> neighborMap;
  YinYangVertexPtr upperLayerVertex = nullptr;
  uint8_t visno;
  YinYangVertex() {

  }
  ~YinYangVertex() {

  }
  /**
   * @brief init a yinyang vertex
   * @param ts the tensor linked to this vertex
   * @param _level the level of this one
   * @param maxNumOfNeighbor the maximum number of neighbors
   * @param _containedTensors the number of contained tensors
   * @param _isYang whether this is a yang vertex
   */
  void init(torch::Tensor &ts, int64_t _level, int64_t maxNumOfNeighbor, int64_t _containedTensors, bool _isYang);
  /**
 * @brief lock this vertex
 */
  void lock() {
    while (!m_mut.try_lock());
  }
  /**
   * @brief unlock this vertex
   */
  void unlock() {
    m_mut.unlock();
  }
  /**
   * @brief attach a tensor with this vertex
   * @param ts the tensor to be attached
   * @note assume ts is a single row
   */
  void attachTensor(torch::Tensor &ts);
  /**
   * @brief detach a tensor with this vertex
   * @param ts the tensor to be detached
   * @note assume ts is a single row
   */
  void detachTensor(torch::Tensor &ts);
  /**
   * @brief to get the nearest vertex of src, start at entryPoint
   * @param src the source vertex to be used as reference
   * @param entryPoint the entryPoint to start greedy search
   * @parm df the distance calculate function
   * @return the nearest vertex
   */
  static YinYangVertexPtr greedySearchForNearestVertex(YinYangVertexPtr src,
                                                       YinYangVertexPtr entryPoint,
                                                       floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
    * @brief to get the nearest vertex of src, start at entryPoint
    * @param src the source tensor to be used as reference
    * @param entryPoint the entryPoint to start greedy search
    * @parm df the distance calculate function
    * @return the nearest vertex
    */
  static YinYangVertexPtr greedySearchForNearestVertex(torch::Tensor &src,
                                                       YinYangVertexPtr entryPoint,
                                                       floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
    * @brief to get k nearest tesnor of src, start at entryPoint
    * @param src the source tensor to be used as reference
    * @param entryPoint the entryPoint to start gready search
    * @param k the number
    * @parm df the distance calculate function
    * @todo This one is just NNDecent greedy policy, perhaps can be better
    * @return the result tensor
    */
  static torch::Tensor greedySearchForKNearestTensor(torch::Tensor &src,
                                                     YinYangVertexPtr entryPoint,
                                                     int64_t k,
                                                     floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
     * @brief to get k nearest vertex of src, start at entryPoint
     * @param src the source vertex to be used as reference
     * @param entryPoint the entryPoint to start gready search
     * @param k the number
     * @param ignoreYin whether or not ignore YinVertex
     * @param forceTheSameLevel whether or not force to find it at the same level
     * @parm df the distance calculate function
     * @todo This one is just NNDecent greedy policy, perhaps can be better
     * @return the nearest vertex
     */
  static std::vector<YinYangVertexPtr> greedySearchForKNearestVertex(YinYangVertexPtr src,
                                                                     YinYangVertexPtr entryPoint,
                                                                     int64_t k,
                                                                     bool ignoreYin,
                                                                     bool forceTheSameLevel,
                                                                     floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
  * @brief to get k nearest vertex of src, start at entryPoint
  * @param src the source tensor
  * @param entryPoint the entryPoint to start gready search
  * @param k the number
  * @param ignoreYin whether or not ignore YinVertex
  * @param forceTheSameLevel whether or not force to find it at the same level
  * @parm df the distance calculate function
  * @todo This one is just NNDecent greedy policy, perhaps can be better
  * @return the nearest vertex
  */
  static std::vector<YinYangVertexPtr> greedySearchForKNearestVertex(torch::Tensor &src,
                                                                     YinYangVertexPtr entryPoint,
                                                                     int64_t k,
                                                                     bool ignoreYin,
                                                                     bool forceTheSameLevel,
                                                                     floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
   * @brief try to connect vertex a and b with each other
   * @param a the new vertex
   * @param b some existing vertex
   * @param vertexMapGe1Vec the vector of vertexMap in all level greater or equal to 1
   * @return whether the connection is established
   */
  static bool tryToConnect(YinYangVertexPtr a,
                           YinYangVertexPtr b,
                           std::vector<YinYangVertexMap> &vertexMapGe1Vec,
                           floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
   * @breif to set the upper layer vertex of this one
   * @param upv the upper layer vertex
   */
  void setUperLayer(YinYangVertexPtr upv) {
    upperLayerVertex = upv;
  }
  /**
  * @breif convert this vertex into string
  * @param shortInfo whether or not shorten the information of tensor filed
  * @return the converted string
  */
  std::string toString(bool shortInfo = true);
};

class YinYangVertexMap {
 protected :
  std::mutex m_mut;
 public:
  std::map<CANDY::YinYangVertexPtr, CANDY::YinYangVertexPtr> vertexMap;
  YinYangVertexMap() {

  }
  YinYangVertexMap(const YinYangVertexMap &other) {
    // Implement the copy constructor to properly copy member variables and base classes
    for (auto &iter : other.vertexMap) {
      this->edit(iter.second);
    }
  }
  ~YinYangVertexMap() {

  }
  /**
* @brief lock this map
*/
  void lock() {
    while (!m_mut.try_lock());
  }
  /**
   * @brief unlock this map
   */
  void unlock() {
    m_mut.unlock();
  }
  /**
* @brief To detect whether a vertex existis in the map
* @param key the vertex pointer as key
* @return bool for the result
  */
  bool exist(CANDY::YinYangVertexPtr key) {
    return (vertexMap.count(key) >= 1);
  }
  /**
  * @brief To edit, i.e., mark the existence of a vertex
  * @param kv the vertex pointer as key
 * @return bool for the result
 */
  void edit(CANDY::YinYangVertexPtr kv) {
    vertexMap[kv] = kv;
  }
  /**
 * @brief To erase, i.e., mark the absence of a vertex
 * @param kv the vertex pointer as key
* @return bool for the result
*/
  void erase(CANDY::YinYangVertexPtr kv) {
    vertexMap.erase(kv);
  }
  /**
   * @brief to get the nearest vertex of src, from a map
   * @param src the source vertex to be used as reference
   * @param vmap, the vertex map
   * @param df, the distance function
   * @return the nearest vertex
   */
  static YinYangVertexPtr nearestVertexWithinMap(YinYangVertexPtr src,
                                                 YinYangVertexMap &vmap,
                                                 floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
    * @brief to get the nearest vertex k of src, from a map
   * @param src the source vertex to be used as reference
   * @param vmap, the vertex map
   * @param k, the number of nearest vertex to be found
   * @param df the distance function
   * @return the nearest vertex
   */
  static std::vector<YinYangVertexPtr> nearestKVertexWithinMap(YinYangVertexPtr src,
                                                               YinYangVertexMap &vmap,
                                                               int64_t k,
                                                               floatDistanceFunction_t df = YinYangGraph_DistanceFunctions::L2Distance);
  /**
   * @brief to get the nearest vertex of src, from the map of this class
   * @param src the source vertex to be used as reference
   * @return the nearest vertex
   */
  YinYangVertexPtr nearestVertexWithinMe(YinYangVertexPtr src);
};
/**
  * @class YinYangGraph_ListCell  CANDY/YinYangIndex/YinYangGraph.h
  * @brief a cell of an ending YinYangVertex
  */
class YinYangGraph_ListCell {
 protected:
  YinYangVertexPtr vertex = nullptr;
  std::mutex m_mut;
  std::vector<uint8_t> encode;
 public:
  YinYangGraph_ListCell() {}
  ~YinYangGraph_ListCell() {}
  /**
  * @brief lock this cell
  */
  void lock() {
    while (!m_mut.try_lock());
  }
  /**
   * @brief unlock this cell
   */
  void unlock() {
    m_mut.unlock();
  }
  void setEncode(std::vector<uint8_t> _encode) {
    encode = _encode;
  }
  std::vector<uint8_t> getEncode() {
    return encode;
  }
  /**
   * @brief insert a tensor
   * @param t the tensor
   * @param maxNeighborCnt the maximum count of neighbors
   * @param yin0Map the map of yin vertex at level 0
   * @param vertexMapGe1Vec the vector of vertexMap in all level greater or equal to 1
   */
  void insertTensor(torch::Tensor &t,
                    int64_t maxNeighborCnt,
                    YinYangVertexMap &yin0Map,
                    std::vector<YinYangVertexMap> &vertexMapGe1Vec);

  /**
  * @brief delete a tensor
   * @note will check the equal condition by torch::equal
  * @param t the tensor
   * @returen bool whether the tensor is really deleted
  */
  bool deleteTensor(torch::Tensor &t);
  /**
   * @brief to get the vertex
   * @return the vertex member
   */
  YinYangVertexPtr getVertex() {
    return vertex;
  }
  // torch::Tensor getAllTensors();

};
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @typedef YinYangGraph_ListCellPtr
 * @brief The class to describe a shared pointer to @ref YinYangGraph_ListCell
 */
typedef std::shared_ptr<CANDY::YinYangGraph_ListCell> YinYangGraph_ListCellPtr;
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @def newYinYangGraph_ListCell
 * @brief (Macro) To creat a new @ref newYinYangGraph_ListCell under shared pointer.
 */
#define  newYinYangGraph_ListCell make_shared<CANDY::YinYangGraph_ListCell>
/**
  * @class YinYangGraph_ListBucket  CANDY/YinYangIndex/YinYangGraph.h
  * @brief a bucket of multiple @ref YinYangGraph_ListCell
  */
class YinYangGraph_ListBucket {
 protected:
  int64_t tensors = 0;
  std::list<YinYangGraph_ListCellPtr> cellPtrs;
  std::mutex m_mut;
 public:
  YinYangGraph_ListBucket() {}
  ~YinYangGraph_ListBucket() {}
  int64_t size() {
    return tensors;
  }
  /**
   * @brief lock this bucket
   */
  void lock() {
    while (!m_mut.try_lock());
  }
  /**
   * @brief unlock this bucket
   */
  void unlock() {
    m_mut.unlock();
  }
  /**
  * @brief insert a tensor with its encode
  * @param t the tensor
  * @param maxNeighborCnt
  * @param encode the corresponding encode
  * @param yin0Map the map of yin vertex at level 0
  * @param vertexMapGe1Vec the vector of vertexMap in all level greater or equal to 1
  * @param isConcurrent whether this process is concurrently executed
   *
  */
  void insertTensorWithEncode(torch::Tensor &t,
                              int64_t maxNeighborCnt,
                              std::vector<uint8_t> &encode,
                              YinYangVertexMap &yin0Map,
                              std::vector<YinYangVertexMap> &vertexMapGe1Vec,
                              bool isConcurrent = false);
  /**
  * @brief delete a tensor with its encode
  * @param t the tensor
  * @param encode the corresponding encode
   * @param isConcurrent whether this process is concurrently executed
   * @return bool whether the tensor is really deleted
  */
  bool deleteTensorWithEncode(torch::Tensor &t, std::vector<uint8_t> &encode, bool isConcurrent = false);
  /**
  * @brief delete a tensor
   * @note will check the equal condition by torch::equal
  * @param t the tensor
   * @param isConcurrent whether this process is concurrently executed
   * * @return bool whether the tensor is really deleted
  */
  bool deleteTensor(torch::Tensor &t, bool isConcurrent = false);
  /**
   * @brief to get the vertex which is linked to an encode, first try exact match, then just return the first one
   * @return the vertex
   */
  YinYangVertexPtr getVertexWithEncode(std::vector<uint8_t> &encode);

};
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @typedef YinYangGraph_ListBucketPtr
 * @brief The class to describe a shared pointer to @ref YinYangGraph_ListBucket
 */
typedef std::shared_ptr<CANDY::YinYangGraph_ListBucket> YinYangGraph_ListBucketPtr;
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @def newYinYangGraph_ListBucket
 * @brief (Macro) To creat a new @ref YinYangGraph_ListBucket under shared pointer.
 */
#define  newYinYangGraph_ListBucket make_shared<CANDY::YinYangGraph_ListBucket>
/**
 * @class YinYangGraph  CANDY/YinYangIndex/YinYangGraph.h
 * @brief The top class of yinyang graph, containing ivf list and critical graph information.
 * - This is a hybrid structure, using encoding-based ranging to assit in graph navigation
 * - This is a hiearchical structure, using high layer yin vertex to summarize data points (marked as yang)
 */
class YinYangGraph {
 protected:
  std::vector<CANDY::YinYangGraph_ListBucketPtr> bucketPtrs;
  int64_t maxConnections = 0;
  size_t encodeLen = 0;
  YinYangVertexMap yin0Map;
  std::vector<YinYangVertexMap> vertexMapGe1Vec;
  static uint8_t getLeftIdxU8(uint8_t idx, uint8_t leftOffset, bool *reachedLeftMost) {
    if (idx < leftOffset) {
      *reachedLeftMost = true;
      return 0;
    }
    return idx - leftOffset;
  }
  static uint8_t getRightIdxU8(uint8_t idx, uint8_t rightOffset, bool *reachedRightMost) {
    uint16_t tempRu = idx;
    tempRu += rightOffset;
    if (tempRu > 255) {
      *reachedRightMost = true;
      return 255;
    }
    return idx + rightOffset;
  }
 public:
  YinYangGraph() {
  }
  /**
   * @brief init this YinYangGraph_List
   * @param bkts the number of buckets
   * @param _encodeLen the length of tensors' encoding
   * @param _maxCon the maximum number of connections in graph vertex
   */
  void init(size_t bkts, size_t _encodeLen, int64_t _maxCon);
  ~YinYangGraph() {}
  /**
 * @brief insert a tensor with its encode
 * @param t the tensor
 * @param encode the corresponding encode
   * @param bktIdx the index number of bucket
  * @param isConcurrent whether this process is concurrently executed
 */
  void insertTensorWithEncode(torch::Tensor &t,
                              std::vector<uint8_t> &encode,
                              uint64_t bktIdx,
                              bool isConcurrent = false);
  /**
  * @brief delete a tensor with its encode
  * @param t the tensor
  * @param encode the corresponding encode
   * @param bktIdx the index number of bucket
   * @param isConcurrent whether this process is concurrently executed
   * @return bool whether the tensor is really deleted
  */
  bool deleteTensorWithEncode(torch::Tensor &t,
                              std::vector<uint8_t> &encode,
                              uint64_t bktIdx,
                              bool isConcurrent = false);

  bool isConcurrent = false;
  /**
   * @brief get minimum number of tensors that are candidate to query t
   * * @param t the tensor
   * @param encode the corresponding encode
   * @param bktIdx the index number of bucket
   * @param isConcurrent whether this process is concurrently executed
   * @return a 2-D tensor contain all, torch::zeros({minimumNum,D}) if got nothing
   */
  torch::Tensor getMinimumNumOfTensors(torch::Tensor &t,
                                       std::vector<uint8_t> &encode,
                                       uint64_t bktIdx,
                                       int64_t minimumNum);

};

} // CANDY

#endif //CANDY_INCLUDE_CANDY_YINGYANGVERTEXINDEX_YINYANGGRAPH_H_
