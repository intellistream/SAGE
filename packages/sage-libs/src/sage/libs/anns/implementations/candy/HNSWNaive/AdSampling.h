/*! \file HNSWNaiveIndex.h*/
//
// Created by Honeta on 2024/4/26.
//

#ifndef CANDY_ADSAMPLING_H
#define CANDY_ADSAMPLING_H
#include <torch/torch.h>

namespace CANDY {
class AdSampling {
 public:
  AdSampling() = default;
  AdSampling(int64_t d):dim(d){};
  static torch::Tensor getTransformMatrix(int64_t dim) {
    torch::manual_seed(time(NULL));
    auto gaus = torch::randn({dim, dim});
    auto [u, s, vh] = torch::linalg::svd(gaus, true, {});
    return u.matmul(vh);
  }

  void set_transformed(torch::Tensor* tm){
      transformMatrix = tm;
  }
  torch::Tensor transform(torch::Tensor ta) {
    return ta.matmul(*transformMatrix);
  }
  void set_threshold(float threshold){
      threshold_ = threshold;
  }

  void set_step(size_t step, float epsilon){
      samplingStep = step;
      epsilon0 = epsilon;
  }
  float distanceCompute_L2(torch::Tensor ta, torch::Tensor tb) {
    auto taPtr = ta.contiguous().data_ptr<float>(), tbPtr = tb.contiguous().data_ptr<float>();
    float dist = 0;
    size_t i = 0;
    while (i < dim) {
      size_t step = std::min(samplingStep, dim - i);
      for (size_t j = 0; j < step; j++) {
        float diff = taPtr[i + j] - tbPtr[i + j];
        dist += diff * diff;
      }
      i += step;
      // Hypothesis tesing
      if (threshold_ > 0 && dist >= threshold_ * ratio(dim, i)) return -1;
    }
    return dist;
  }

 private:
  size_t samplingStep = 64;
  float epsilon0 = 1.0; // recommended in [1.0,4.0], valid in in [0, +\infty)

  size_t dim;
  torch::Tensor* transformMatrix;
  float threshold_;
  inline float ratio(const int &dim, const int &i) {
    if (i == dim) return 1.0;
    auto temp = 1.0 + epsilon0 / std::sqrt(i);
    return 1.0 * i / dim * temp * temp;
  }
};
}  // namespace CANDY

#endif
