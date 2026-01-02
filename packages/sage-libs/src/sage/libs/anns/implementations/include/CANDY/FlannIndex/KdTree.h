//
// Created by Isshin on 2024/3/23.
//

#ifndef CANDY_KDTREE_H
#define CANDY_KDTREE_H
#include <CANDY/FlannIndex/FlannComponent.h>

namespace CANDY {
class KdTree : public FlannComponent {
  int RAND_DIM = 5;
  int SAMPLE_MEAN = 114;
 public:
  struct Node {
   public:
    /// index used for subdivision.
    int64_t divfeat;
    /// The value used for subdivision
    float divval;
    /// Node data
    torch::Tensor data;
    Node *child1, *child2;

    Node() {
      child1 = nullptr;
      child2 = nullptr;
    }

    ~Node() {
      if (child1 != nullptr) {
        child1->~Node();
        child1 = nullptr;
      }
      if (child2 != nullptr) {
        child2->~Node();
        child2 = nullptr;
      }
    }
  };
  typedef Node *NodePtr;
  typedef FLANN::BranchStruct<NodePtr> BranchSt;
  typedef BranchSt *Branch;

  /// Number of randomized trees that are used in forest
  uint64_t num_trees;
  float *mean;
  float *var;

  /// array of num_trees to specify roots
  std::vector<NodePtr> tree_roots;
  KdTree() {
    mean = 0;
    var = 0;
    ntotal = 0;
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
   */
  void addPointToTree(NodePtr node, int64_t idx);
  /**
   * @brief add data into the tree either by reconstruction or appending
   * @param t new data
   */
  virtual void addPoints(torch::Tensor &t) override;
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
   * @brief
   * @param result
   * @param vec
   * @param maxCheck
   * @param epsError
   */
  void getNeighbors(FLANN::ResultSet &result, const float *vec, int maxCheck, float epsError);
  /**
   * @brief search from a given node of the tree
   * @param result priority queue to store results
   * @param vec vector to be searched
   * @param node current node to be traversed
   * @param mindist current minimum distance obtained
   * @param checkCount count of checks on multiple trees
   * @param maxCheck max check on multiple trees
   * @param epsError error to be compared with worst distance
   * @param heap heap structure to store branches
   * @param checked visited bitmap
   */
  void searchLevel(FLANN::ResultSet &result,
                   const float *vec,
                   NodePtr node,
                   float mindist,
                   int &checkCount,
                   int maxCheck,
                   float epsError,
                   FLANN::Heap<BranchSt> *heap,
                   FLANN::VisitBitset &checked);
  /**
   * @brief build the tree from scratch
   */
  void buildTree();

  /**
   * @brief create a node that subdivides vectors from data[first] to data[last]. Called recursively on each subset
   * @param idx index of this vector
   * @param count number of vectors in this sublist
   * @return
   */
  NodePtr divideTree(int64_t *idx, int count);

  /**
   * @brief choose which feature to use to subdivide this subset of vectors by randomly choosing those with highest variance
   * @param ind index of this vector
   * @param count number of vectors in this sublist
   * @param index index where the sublist split
   * @param cutfeat index of highest variance as cut feature
   * @param cutval value of highest variance
   */
  void meanSplit(int64_t *ind, int count, int64_t &index, int64_t &cutfeat, float &cutval);

  /**
   * @brief select top RAND_DIM largest values from vector and return index of one of them at random
   * @param v values of variance
   * @return the index of randomly chosen highest variance
   */
  int selectDivision(float *v);

  /**
   * @brief subdivide the lists by a plane perpendicular on axe corresponding to the cutfeat dimension at cutval position
   * @param ind index of the list
   * @param count count of the list
   * @param cutfeat the chosen feature
   * @param cutval the threshold value to be compared
   * @param lim1 split index candidate for meansplit
   * @param lim2 split index candidate for meansplit
   */
  void planeSplit(int64_t *ind, int count, int64_t cutfeat, float cutval, int &lim1, int &lim2);
};

}
#endif //CANDY_KDTREE_H
