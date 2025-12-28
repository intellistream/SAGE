//
// Created by Isshin on 2024/3/23.
//

#ifndef CANDY_KMEANS_H
#define CANDY_KMEANS_H
#include <FlannIndex/FlannComponent.h>
namespace CANDY {
/**
 * @class KmeansTree CANDY/FlannIndex/Kmeanss.h
 * @brief The structure representing hierarchical k-means tree used in FLANN
 */
class KmeansTree : public FlannComponent {
 public:

  struct NodeInfo {
    int64_t index;
    torch::Tensor point;
  };

  struct Node {
    /// Cluster center
    float *pivot;
    /// Cluster radius
    float radius;
    /// Cluster variance
    float variance;
    /// Cluster size
    int64_t size;
    /// child nodes
    std::vector<Node *> childs;
    /// node points
    std::vector<NodeInfo> points;

    ~Node() {
      delete[] pivot;
      if (!childs.empty()) {
        for (size_t i = 0; i < childs.size(); i++) {
          childs[i]->~Node();
        }
      }
    }
  };
  typedef Node *NodePtr;
  typedef FLANN::BranchStruct<NodePtr> BranchSt;
  typedef BranchSt *Branch;

  /// branching factor used in clustering
  int64_t branching;
  /// number of max iterations when clustering
  int64_t iterations;
  /// Cluster border index used in tree search when choosing the closest cluster to search next;
  double cb_index = 0.4;
  /// root of tree
  NodePtr root;
  /// the center chooser in clustering; currently only implemented randomChooser
  FLANN::RandomCenterChooser *centerChooser;

  faiss::MetricType faissMetric = faiss::METRIC_L2;

  KmeansTree() {
    ntotal = 0;
    root = nullptr;
  }
  /**
  * @brief set the index-specific config related to one index
  * @param cfg the config of this class
  * @return bool whether the configuration is successful
  */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg) override;

  /**
   * @brief add dbTensor[idx] to tree with root as node
   * @param node typically a tree root
   * @param idx index in dbTensor
   * @param dist
   */
  void addPointToTree(NodePtr node, int64_t idx, float dist);
  /**
   * @brief add data into the tree either by reconstruction or appending
   * @param t new data
   */
  virtual void addPoints(torch::Tensor &t) override;
  /**
   * @brief compute the radius, variance and mean for this cluster
   * @param node the node representing the cluster
   * @param indices the indexes within the cluster
   */
  void computeNodeStat(NodePtr node, std::vector<int64_t> &indices);
  /**
   * #brief compute the cluster iteratively
   * @param node the node where the cluster starts
   * @param indices indexes to be involved
   * @param indices_length length of indexes to be involved
   * @param branching number of branching in tree
   */
  void computeClustering(NodePtr node, int64_t *indices, int64_t indices_length, int64_t branching);

  /**
   * @brief perform knn-search on the kdTree structure
   * @param q query data to be searched
   * @param idx result vectors indices
   * @param distances result vectors' distances with query
   * @param aknn number of approximate neighbors
   * @return number of results obtained
   */
  virtual int knnSearch(torch::Tensor &q, int64_t *idx, float *distances, int64_t aknn) override;
  /**
   * @brief set the params from auto-tuning
   * @param param best param
   * @return true if success
   */
  virtual bool setParams(FlannParam param) override;
  /**
   * @brief called by knnSearch, to search the vec within the true
   * @param result result set
   * @param vec vector to be searched
   * @param maxCheck max times to check
   */
  void getNeighbors(FLANN::ResultSet &result, float *vec, int maxCheck);
  /**
   * @brief explore from the node for the closest center
   * @param node node to be explored
   * @param q query vector
   * @param heap heap set
   * @return the index of center
   */
  int64_t explore(NodePtr node, float *q, FLANN::Heap<BranchSt> *heap);
  /**
   * @brief practice KNN search
   * @param node starting node
   * @param result result set
   * @param vec query vector
   * @param check current check time
   * @param maxCheck max check times
   * @param heap heap set
   */
  void findNN(NodePtr node,
              FLANN::ResultSet &result,
              float *vec,
              int &check,
              int maxCheck,
              FLANN::Heap<BranchSt> *heap);
};
}

#endif //CANDY_KMEANS_H
