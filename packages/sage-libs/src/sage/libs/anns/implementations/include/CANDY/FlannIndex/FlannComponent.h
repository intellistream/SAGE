//
// Created by Isshin on 2024/3/25.
//

#ifndef CANDY_FLANNCOMPONENT_H
#define CANDY_FLANNCOMPONENT_H
#include<CANDY/FlannIndex/FlannUtils.h>
#define FLANN_AUTO 0
#define FLANN_KDTREE 1
#define FLANN_KMEANS 2
namespace CANDY {
typedef int64_t flann_index_t;
struct FlannParam {
  flann_index_t flann_index;
  // for kdtree
  int64_t num_trees;
  // for kmeans
  double cb_index;
  int64_t branching;
  int64_t maxIterations;

  uint64_t searchTime;
  uint64_t buildTime;

};
class FlannComponent {

 public:
  int64_t vecDim;
  uint64_t ntotal;
  int checks = 32;
  float eps = 0.0;
  int64_t lastNNZ;
  int64_t expandStep;
  /// Pointer dataset
  torch::Tensor dbTensor;
  faiss::MetricType faissMetric = faiss::METRIC_L2;

  virtual void addPoints(torch::Tensor &t) {
    bool success = INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &t, &lastNNZ, expandStep);
    assert(success);
  };

  virtual int knnSearch(torch::Tensor &q, int64_t *idx, float *distances, int64_t aknn) {
    assert(idx);
    assert(distances);
    auto dim = q.size(1);
    assert(dim == vecDim);
    assert(aknn != 0);
    return -1;
  };

  virtual bool setConfig(INTELLI::ConfigMapPtr cfg) {
    assert(cfg);
    dbTensor = torch::zeros({0, (int64_t) vecDim});
    lastNNZ = -1;
    expandStep = 100;
    return true;
  };
  /**
  * @brief set the params from auto-tuning
  * @param param best param
  * @return true if success
  */
  virtual bool setParams(FlannParam param) {
    assert(param.flann_index == FLANN_KMEANS || param.flann_index == FLANN_KDTREE);
    return true;
  }

};
}
#endif //CANDY_FLANNCOMPONENT_H
