//
// Created by haolan on 5/26/23.
//

#include <CPPAlgos/CRSV2CPPAlgo.h>

namespace LibAMM {
torch::Tensor LibAMM::CRSV2CPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t k2) {
  A = A.t();
  auto A_size = A.sizes();
  int64_t n = A_size[0];
  // int64_t m = A_size[1];
  int64_t k = (int64_t) k2;
  assert(n == B.size(0));
  //TORCH_CHECK(n == B.size(0));
  //TORCH_CHECK(k < n);

  //INTELLI_INFO("Running CRS V2 CPP");

  // probability distribution
  torch::Tensor sample = torch::rand({n}); // default: uniform

  // diagonal scaling matrix D (nxn)
  sample = sample.div(sample.sum());
  torch::Tensor D = torch::diag(1.0 / torch::sqrt(k * sample));

  // sampling matrix S (kxn)
  torch::Tensor column_indices = torch::multinomial(sample, k, true);
  torch::Tensor S = torch::zeros({k, n});
  for (int64_t row = 0; row < k; row++) {
    int64_t col = column_indices[row].item<int64_t>();
    S[row][col] = 1;
  }

  torch::Tensor a = torch::matmul(torch::matmul(A.t(), D), S.t());
  torch::Tensor b = torch::matmul(torch::matmul(a, S), D);

  return torch::matmul(b, B);
}
} // LibAMM
