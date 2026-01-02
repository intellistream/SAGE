//
// Created by haolan on 5/29/23.
//
#include <CPPAlgos/BCRSCPPAlgo.h>

namespace LibAMM {
torch::Tensor BCRSCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t k2) {
  A = A.t();
  auto A_size = A.sizes();
  int64_t n = A_size[0];
  //int64_t m = A_size[1];
  int64_t k = (int64_t) k2;
  assert(n == B.size(0));
  //TORCH_CHECK(n == B.size(0));
  //TORCH_CHECK(k < n);

  //INTELLI_INFO("Running Bernoulli CRS CPP");

  // probability distribution
  torch::Tensor sample = torch::rand({n}); // default: uniform
  sample = sample.div(sample.sum() / k);  // sum = k as per the paper

  // diagonal scaling matrix P (nxn)
  torch::Tensor P = torch::diag(1.0 / torch::sqrt(sample));

  // random diagonal sampling matrix K (nxn)
  sample = (torch::rand({n}) < sample).to(torch::kFloat32);
  torch::Tensor K = torch::diag(sample);

  torch::Tensor a = torch::matmul(torch::matmul(A.t(), P), K);
  torch::Tensor b = torch::matmul(torch::matmul(a, K), P);

  return torch::matmul(b, B);
}
}
