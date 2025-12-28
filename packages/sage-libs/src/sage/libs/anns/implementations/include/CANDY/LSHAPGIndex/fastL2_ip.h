#ifndef _FASTL2_IP_H
#define _FASTL2_IP_H
#include <torch/torch.h>

namespace fastlib {

}

inline float calL2Sqr_fast(float *v1, float *v2, int dim) {

  // Create tensors from the input arrays
  auto t1 = torch::from_blob(v1, {dim}, torch::kFloat);
  auto t2 = torch::from_blob(v2, {dim}, torch::kFloat);

  // Calculate the squared L2 distance as ||v1 - v2||^2
  auto diff = t1 - t2;
  auto l2_sqr = torch::sum(diff * diff);

  // Convert the result back to float and return
  return l2_sqr.item<float>();

}

inline float calIp_fast(float *v1, float *v2, int dim) {
  auto t1 = torch::from_blob(v1, {dim}, torch::kFloat);
  auto t2 = torch::from_blob(v2, {dim}, torch::kFloat);

  // Calculate the inner (dot) product
  auto inner_product = torch::dot(t1, t2);

  // Convert the result back to float and return
  return inner_product.item<float>();

}

#endif
