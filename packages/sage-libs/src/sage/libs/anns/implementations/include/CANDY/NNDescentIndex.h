/*! \file NNDescentIndex.h*/
//
// Created by honeta on 21/02/24.
//

#ifndef CANDY_INCLUDE_CANDY_NNDESCENTINDEX_H_
#define CANDY_INCLUDE_CANDY_NNDESCENTINDEX_H_

#include <CANDY/AbstractIndex.h>

#include <functional>
#include <random>
#include <unordered_set>

namespace CANDY {

/**
 * @ingroup  CANDY_lib_container
 * @{
 */
/**
 * @class NNDescentIndex CANDY/NNDescentIndex.h
 * @brief An index whose core algorithm is only used for offline construction,
 * but based on its main data structure we have implemented online update
 * operations that need to be optimized.
 * @note special parameters
 *  - parallelWorkers The number of paraller workers, I64, default 1 (set this
 * to less than 0 will use max hardware_concurrency);
 *  - vecDim, the dimension of vectors, default 768, I64
 *  - graphK, the neighbors of every node in internal data struct, default 20,
 * I64
 *  - rho, sample proportion in NNDescent algorithm which takes effect in
 * offline build only (larger is higher accuracy but lower speed), default 1.0,
 * F64
 *  - delta, loop termination condition in NNDescent algorithm which takes
 * effect in offline build only (smaller is higher accuracy but lower speed),
 * default 0.01, F64
 * @warnning
 * Make sure you are using 2D tensors!
 */
class NNDescentIndex : public CANDY::AbstractIndex {
 protected:
  struct Neighbor {
    size_t id;
    double distance;
    bool flag;

    Neighbor() = default;
    Neighbor(size_t id, double distance, bool f)
        : id(id), distance(distance), flag(f) {}

    inline bool operator<(const Neighbor &other) const {
      return distance < other.distance;
    }
  };

  struct Nhood {
    std::mutex poolLock;
    std::vector<Neighbor> pool;  // candidate pool (a max heap)
    std::unordered_set<size_t> neighborIdxSet;

    std::unordered_set<size_t> nnOld;  // old neighbors
    std::unordered_set<size_t> nnNew;  // new neighbors
    std::mutex rnnOldLock;
    std::unordered_set<size_t> rnnOld;  // reverse old neighbors
    std::mutex rnnNewLock;
    std::unordered_set<size_t> rnnNew;  // reverse new neighbors

    Nhood() = default;
    Nhood(const Nhood &other)
        : pool(other.pool),
          neighborIdxSet(other.neighborIdxSet),
          nnOld(other.nnOld),
          nnNew(other.nnNew),
          rnnOld(other.rnnOld),
          rnnNew(other.rnnNew) {}
  };

  void nnDescent();
  void randomSample(std::mt19937 &rng, std::vector<size_t> &vec, size_t n,
                    size_t sampledCount);
  bool updateNN(size_t i, size_t j, double dist);
  double calcDist(const torch::Tensor &ta, const torch::Tensor &tb);
  torch::Tensor searchOnce(torch::Tensor q, int64_t k);
  std::vector<std::pair<double, size_t>> searchOnceInner(torch::Tensor q,
                                                         int64_t k);
  bool insertOnce(vector<std::pair<double, size_t>> &neighbors,
                  torch::Tensor t);
  bool deleteOnce(torch::Tensor t, int64_t k);
  void parallelFor(size_t idxSize, std::function<void(size_t)> action);

  int64_t graphK, parallelWorkers, vecDim, frozenLevel;
  double rho, delta;
  std::vector<Nhood> graph;
  std::vector<torch::Tensor> tensor;
  std::unordered_set<size_t> deletedIdxSet;

 public:
  NNDescentIndex() = default;
  ~NNDescentIndex() = default;
  /**
   * @brief load the initial tensors of a data base, use this BEFORE @ref
   * insertTensor
   * @note This is majorly an offline function, and may be different from @ref
   * insertTensor for some indexes
   * @param t the tensor, some index need to be single row
   * @return bool whether the loading is successful
   */
  virtual bool loadInitialTensor(torch::Tensor &t);
  /**
   * @brief reset this index to inited status
   */
  virtual void reset();
  /**
   * @brief set the index-specfic config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief insert a tensor
   * @param t the tensor, some index need to be single row
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensor(torch::Tensor &t);

  /**
   * @brief delete a tensor
   * @param t the tensor, some index needs to be single row
   * @param k the number of nearest neighbors
   * @return bool whether the deleting is successful
   */
  virtual bool deleteTensor(torch::Tensor &t, int64_t k = 1);

  /**
   * @brief revise a tensor
   * @param t the tensor to be revised
   * @param w the revised value
   * @return bool whether the revising is successful
   * @note only support to delete and insert, no straightforward revision
   */
  virtual bool reviseTensor(torch::Tensor &t, torch::Tensor &w);

  /**
   * @brief return a vector of tensors according to some index
   * @param idx the index, follow faiss's style, allow the KNN index of multiple
   * queries
   * @param k the returned neighbors, i.e., will be the number of rows of each
   * returned tensor
   * @return a vector of tensors, each tensor represent KNN results of one query
   * in idx
   */
  virtual std::vector<torch::Tensor> getTensorByIndex(
      std::vector<faiss::idx_t> &idx, int64_t k);
  /**
   * @brief return the rawData of tensor
   * @return The raw data stored in tensor
   */
  virtual torch::Tensor rawData();
  /**
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);

  /**
   * @brief some extra set-ups if the index has HPC fetures
   * @return bool whether the HPC set-up is successful
   */
  virtual bool startHPC();
  /**
   * @brief some extra termination if the index has HPC fetures
   * @return bool whether the HPC termination is successful
   */
  virtual bool endHPC();
  /**
   * @brief set the frozen level of online updating internal state
   * @param frozenLv the level of frozen, 0 means freeze any online update in
   * internal state
   * @return whether the setting is successful
   */
  virtual bool setFrozenLevel(int64_t frozenLv);
  /**
   * @brief offline build phase
   * @param t the tensor for offline build
   * @return whether the building is successful
   */
  virtual bool offlineBuild(torch::Tensor &t);
};

/**
 * @ingroup  CANDY_lib_container
 * @typedef NNDescentIndexPtr
 * @brief The class to describe a shared pointer to @ref  NNDescentIndex

 */
typedef std::shared_ptr<class CANDY::NNDescentIndex> NNDescentIndexPtr;
/**
 * @ingroup  CANDY_lib_container
 * @def newNNDescentIndex
 * @brief (Macro) To creat a new @ref  NNDescentIndex shared pointer.
 */
#define newNNDescentIndex std::make_shared<CANDY::NNDescentIndex>
}  // namespace CANDY
/**
 * @}
 */

#endif
