//
// Created by Isshin on 2024/3/25.
//

#ifndef CANDY_FLANNUTILS_H
#define CANDY_FLANNUTILS_H
#include <CANDY.h>
#include <faiss/utils/distances.h>
namespace CANDY::FLANN {

template<typename T>
/**
 * @class BranchStruct CANDY/FlannIndex/FlannUtils.h
 * @brief The structure representing a branch point when finding neighbors in the tree
 */
struct BranchStruct {
  T node;
  float mindist;
  BranchStruct() {};
  BranchStruct(const T &n, float dist) : node(n), mindist(dist) {};
  bool operator<(const BranchStruct<T> &right) const {
    return mindist < right.mindist;
  }
};

/**
 * @class DistanceIndex CANDY/FlannIndex/FlannUtils.h
 * @brief The structure representing a vectors' distance with the query along with its index
 */
struct DistanceIndex {
  float dist;
  int64_t index;
  DistanceIndex(float d, int64_t i) : dist(d), index(i) {};
  bool operator<(const DistanceIndex &right) const {
    return (dist < right.dist) || ((dist == right.dist) && (index < right.index));
  }
};

/**
 * @class ResultSet CANDY/FlannIndex/FlannUtils.h
 * @brief a priority queue used in FlannIndex
 */
class ResultSet {
 public:
  ResultSet(int64_t capacity) {
    this->capacity = capacity;
    dist_index.reserve(capacity);
    dist_index.clear();
    worst_distance = std::numeric_limits<float>::max();
    is_full = false;
  }

  ~ResultSet() {};

  size_t size() const {
    return dist_index.size();
  }

  bool isFull() {
    return is_full;
  }

  float worstDist() {
    return worst_distance;
  }
  void add(float dist, int64_t index) {
    if (dist >= worst_distance) return;
    if (dist_index.size() == capacity) {
      std::pop_heap(dist_index.begin(), dist_index.end());
      dist_index.pop_back();
    }

    dist_index.push_back(DistanceIndex(dist, index));
    if (is_full) {
      std::push_heap(dist_index.begin(), dist_index.end());
    }

    if (dist_index.size() == capacity) {
      if (!is_full) {
        std::make_heap(dist_index.begin(), dist_index.end());
        is_full = true;
      }
      worst_distance = dist_index[0].dist;
    }
  }

//    void copy(int64_t* indices, float* dists, int64_t num_elements){
//        std::sort(dist_index.begin(), dist_index.end());
//
//        int64_t n =  std::min(dist_index.size(), (size_t)num_elements);
//        printf("copying\n");
//        for(int64_t i=0; i<n;i++){
//            printf("%ld %f\n", dist_index[i].index, dist_index[i].dist);
//            *indices++ = dist_index[i].index;
//            *dists++= dist_index[i].dist;
//        }
//    }

  void copy(int64_t *indices, float *dists, int64_t q, int64_t num_elements) {
    std::sort(dist_index.begin(), dist_index.end());

    int64_t n = std::min(dist_index.size(), (size_t) num_elements);
    for (int64_t i = 0; i < n; i++) {
      //printf("%ld %f\n", dist_index[i].index, dist_index[i].dist);
      indices[q * n + i] = dist_index[i].index;
      dists[q * n + i] = dist_index[i].dist;
    }
  }
 private:
  size_t capacity;
  float worst_distance;
  std::vector<DistanceIndex> dist_index;
  bool is_full;

};
/**
 * @class VisitedBitset CANDY/FlannIndex/FlannUtils.h
 * @brief The visited array of nodes
 */
class VisitBitset {
 public:
  VisitBitset() : size(0) {};
  VisitBitset(size_t s) : size(s) {}

  void clear() {
    std::fill(bitset.begin(), bitset.end(), 0);
  }

  bool empty() {
    return bitset.empty();
  }
  void reset(int64_t index) {
    bitset[index / cell_bit_size] &= ~(size_t(1) << (index % cell_bit_size));
  }

  void reset_block(int64_t index) {
    bitset[index / cell_bit_size] = 0;
  }

  void resize(size_t s) {
    size = s;
    bitset.resize(size / cell_bit_size + 1);
  }

  void set(int64_t index) {
    bitset[index / cell_bit_size] |= size_t(1) << (index % cell_bit_size);
  }

  size_t getSize() {
    return size;
  }

  bool test(int64_t index) {
    bool result = (bitset[index / cell_bit_size] & (size_t(1) << (index % cell_bit_size))) != 0;
    return result;
  }

 private:
  std::vector<size_t> bitset;
  size_t size;
  static const unsigned int cell_bit_size = CHAR_BIT * sizeof(size_t);
};

template<typename T>
/**
 * @class Heap CANDY/FlannIndex/FlannUtils.h
 * @brief heap structure used by FlannIndex
 */
class Heap {
  std::vector<T> heap;
  int64_t length;
  int64_t count;

 public:
  Heap(int64_t size) {
    length = size;
    heap.reserve(length);
    count = 0;
  }
  int64_t size() {
    return count;
  }

  bool empty() {
    return size() == 0;
  }

  void clear() {
    heap.clear();
    count = 0;
  }

  void insert(const T &t) {
    if (count == length) {
      return;
    }
    heap.push_back(t);
    std::push_heap(heap.begin(), heap.end());
    ++count;
  }

  bool popMin(T &value) {
    if (count == 0) {
      return false;
    }
    value = heap[0];
    std::pop_heap(heap.begin(), heap.end());
    heap.pop_back();
    --count;
    return true;
  }
};
/**
 * @class UniqueRandom CANDY/FlannIndex/FlannUtils.h
 * @brief The class to output unique random values
 */
class UniqueRandom {
  std::vector<int64_t> vals;
  int64_t size;
  int64_t counter;

 public:
  void init(int64_t n) {
    vals.resize(n);
    size = n;
    for (int64_t i = 0; i < size; i++) {
      vals[i] = i;
    }

    std::random_device rd;
    std::mt19937 g(rd());
    std::shuffle(vals.begin(), vals.end(), g);
    counter = 0;
  }
  UniqueRandom(int64_t n) {
    init(n);
  }

  int64_t next() {
    if (counter == size) {
      return (int64_t) -1;
    } else {
      return vals[counter++];
    }
  }
};

/**
 * @class RandomCenterChooser CANDY/FlannIndex/FlannUtils.h
 * @brief The class used in hierarchical kmeans tree to choose center
 */
class RandomCenterChooser {
  torch::Tensor *points;
  int64_t vecDim;
 public:

  RandomCenterChooser(torch::Tensor *p, int64_t v) {
    points = p;
    vecDim = v;
  }

  void operator()(int64_t k, int64_t *indices, int64_t indices_length, int64_t *centers, int64_t &centers_length) {
    UniqueRandom r(indices_length);

    int64_t index;
    for (index = 0; index < k; index++) {
      bool duplicate = true;
      int64_t rnd;
      while (duplicate) {
        duplicate = false;
        rnd = r.next();
        if (rnd < 0) {
          centers_length = index;
          return;
        }

        centers[index] = indices[rnd];
        for (int j = 0; j < index; j++) {
          auto a = points->slice(0, centers[index], centers[index] + 1).contiguous().data_ptr<float>();
          auto b = points->slice(0, centers[j], centers[j] + 1).contiguous().data_ptr<float>();
          auto sq = faiss::fvec_L2sqr(a, b, vecDim);
          if (sq < 1e-16) {
            duplicate = true;
          }
        }
      }
    }
    centers_length = index;
  }
};
}
#endif //CANDY_FLANNUTILS_H
