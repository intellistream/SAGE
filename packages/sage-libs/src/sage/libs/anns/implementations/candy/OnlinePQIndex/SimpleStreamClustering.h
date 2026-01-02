/*! \file SimpleStreamClustering.h*/
//
// Created by tony on 11/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_ONLINEPQINDEX_SIMPLESTREAMCLUSTERING_H_
#define CANDY_INCLUDE_CANDY_ONLINEPQINDEX_SIMPLESTREAMCLUSTERING_H_
#include <Utils/IntelliTensorOP.hpp>
#include <vector>
namespace CANDY {

// Distance function type (function pointer), data, centroid
using DistanceFunction_t = torch::Tensor (*)(const torch::Tensor &, const torch::Tensor &);
using UpdateFunction_t = void (*)(const torch::Tensor *, torch::Tensor *, const int64_t);
/**
 *  @ingroup  CANDY_lib_bottom_sub The support classes for index approaches
 * @{
 */
/**
 * @class SimpleStreamClustering CANDY/OnlinePQIndex/SimpleStreamClustering.h
 * @brief a simple class for stream clustering, following online PQ style and using simple linear equations
 * @todo two functions are extremely slow and costly, needs to be re-implemented
 *  - @ref buildCentroids
 *  - @ref classifyMultiRow
 */
class SimpleStreamClustering {
 protected:
  torch::Tensor myCentroids;
  std::vector<int64_t> myDataCntInCentroid;
 public:
  SimpleStreamClustering() {}
  ~SimpleStreamClustering() {}
  /**
   * @brief the default euclidean distance function
   * @param a the data tensor
   * @param b the centroids
   * @return the aligned distance tensor
   */
  static torch::Tensor euclideanDistance(const torch::Tensor &a, const torch::Tensor &b) {
    // Assuming 'a' has shape (N, D) and 'b' has shape (K, D)
    torch::Tensor expandedA = a.unsqueeze(1).expand({a.size(0), b.size(0), a.size(1)});
    torch::Tensor expandedB = b.unsqueeze(0).expand({a.size(0), b.size(0), b.size(1)});
    return (expandedA - expandedB).pow(2).sum(2);
  }
  /**
    * @brief the default euclidean insert function
    * @param a the data tensor
    * @param b the centroids
    * @param c the number of points in this centroid
    * @return the aligned distance tensor
    */
  static void euclideanInsert(const torch::Tensor *a, torch::Tensor *b, const int64_t c) {
    *b = *b + (*a - *b) / c;
  }
  /**
   * @brief the default euclidean delete function
   * @param a the data tensor
   * @param b the centroids
   * @param c the number of points in this centroid
   * @return the aligned distance tensor
   */
  static void euclideanDelete(const torch::Tensor *a, torch::Tensor *b, const int64_t c) {
    *b = *b - (*a - *b) / c;
  }
  /**
   * @brief to build the centroids from trainset
   * @param trainSet the trainset, N*D
   * @param k the number of centroids
   * @param maxIterations the max iteratiosn for setting up cluesters
   * @param distanceFunc the distance function
   * @param usingCuda whether or not using cuda
   * @return whether the build is successful
   */
  bool buildCentroids(torch::Tensor &trainSet,
                      int64_t k,
                      int64_t maxIterations,
                      DistanceFunction_t distanceFunc = SimpleStreamClustering::euclideanDistance,
                      bool usingCuda = true);
  /**
   * @brief export the inside tensor of centroids to outside
   * @return the myCentroids tensor
   */
  torch::Tensor exportCentroids(void) {
    return myCentroids;
  }
  /**
   * @brief save the centroids to file
   * @param fname the name of file
   * @return whether the saving is successful
   */
  bool saveCentroidsToFile(std::string fname) {
    return INTELLI::IntelliTensorOP::tensorToFile(&myCentroids, fname);
  }
  /**
   * @brief to load centroids from external tensor
   * @param externCentroid the external tensor of centroid
   * @return whether the load is successful
   */
  bool loadCentroids(torch::Tensor &externCentroid);
  /**
   * @brief to load centroids from external file
   * @param fname the file name of external tensor
   * @return whether the load is successful
   */
  bool loadCentroids(std::string fname);
  /**
   * @brief classify a single row of tensor
   * @param rowTensor the 1*D row tensor
   * @param distanceFunc the distance function
   * @return the idx of cluster it belongs to
   */
  int64_t classifySingleRow(torch::Tensor &rowTensor,
                            DistanceFunction_t distanceFunc = SimpleStreamClustering::euclideanDistance);
  /**
  * @brief classify multi rows of tensor
  * @param rowsTensor the N*D row tensor
  * @param distanceFunc the distance function
  * @return the idx of cluster it belongs to
  */
  std::vector<int64_t> classifyMultiRow(torch::Tensor &rowTensor,
                                        DistanceFunction_t distanceFunc = SimpleStreamClustering::euclideanDistance);
  /**
   *  @brief add a single row of tensor
   * @param rowTensor the 1*D row tensor
   * @param insertFunc the insert function
   * @param frozenLevel  the level of frozen, 0 means freeze any  online update in internal state
   * @ param distanceFunc the distance function
   * @return whether the add is successful
   */
  bool addSingleRow(torch::Tensor &rowTensor,
                    int64_t frozenLevel = 0,
                    UpdateFunction_t insertFunc = SimpleStreamClustering::euclideanInsert,
                    DistanceFunction_t distanceFunc = SimpleStreamClustering::euclideanDistance);
  /**
   *  @brief add a single row of tensor, with specifying its cluster index
   * @param rowTensor the 1*D row tensor
   * @param clusterIdx the cluster index
   * @param insertFunc the insert function
   * @param frozenLevel  the level of frozen, 0 means freeze any  online update in internal state
   * @ param distanceFunc the distance function
   * @return whether the add is successful
   */
  bool addSingleRowWithIdx(torch::Tensor &rowTensor, int64_t clusterIdx,
                           int64_t frozenLevel = 0,
                           UpdateFunction_t insertFunc = SimpleStreamClustering::euclideanInsert,
                           DistanceFunction_t distanceFunc = SimpleStreamClustering::euclideanDistance);
  /**
  *  @brief delete a single row of tensor
  * @param rowTensor the 1*D row tensor
  * @param deleteFunc  the delete function
  * @param frozenLevel  the level of frozen, 0 means freeze any online update in internal state
   *  @ param distanceFunc the distance function
  * @return whether the delete is successful
  */
  bool deleteSingleRow(torch::Tensor &rowTensor,
                       int64_t frozenLevel = 0,
                       UpdateFunction_t deleteFunc = SimpleStreamClustering::euclideanDelete,
                       DistanceFunction_t distanceFunc = SimpleStreamClustering::euclideanDistance);
  /**
   *  @brief delete a single row of tensor, with specifying its cluster index
   * @param rowTensor the 1*D row tensor
   * @param clusterIdx the cluster index
   * @param deleteFunc the delete function
   * @param frozenLevel  the level of frozen, 0 means freeze any  online update in internal state
   * @ param distanceFunc the distance function
   * @return whether the deletion is successful
   */
  bool deleteSingleRowWithIdx(torch::Tensor &rowTensor, int64_t clusterIdx,
                              int64_t frozenLevel = 0,
                              UpdateFunction_t deleteFunc = SimpleStreamClustering::euclideanInsert,
                              DistanceFunction_t distanceFunc = SimpleStreamClustering::euclideanDistance);
};
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @typedef SimpleStreamClusteringPtr
 * @brief The class to describe a shared pointer to @ref SimpleStreamClustering
 */
typedef std::shared_ptr<CANDY::SimpleStreamClustering> SimpleStreamClusteringPtr;
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @def newSimpleStreamClustering
 * @brief (Macro) To creat a new @ref SimpleStreamClustering under shared pointer.
 */
#define  newSimpleStreamClustering make_shared<CANDY::SimpleStreamClustering>
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_CANDY_ONLINEPQINDEX_SIMPLESTREAMCLUSTERING_H_
