//
// Created by haolan on 5/29/23.
//

#include <CPPAlgos/EWSCPPAlgo.h>

namespace LibAMM {
torch::Tensor LibAMM::EWSCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t k2) {
  auto A_size = A.sizes();
  int64_t m = A_size[0];
  int64_t n = A_size[1];
  int64_t k = (int64_t) k2;
  TORCH_CHECK(n == B.size(0));
  TORCH_CHECK(k < n);

  int64_t p = B.size(1);

  // probability distribution
  torch::Tensor probs = torch::rand({m, n});

  // S matrix that samples A with scaling
  torch::Tensor mask = torch::rand_like(probs) < probs;
  torch::Tensor S = torch::zeros_like(A);
  S.masked_scatter_(mask, A.masked_select(mask) / probs.masked_select(mask));

  // R matrix that samples B with scaling
  torch::Tensor probs_r = torch::rand({n, p});  // a different probabilistic distribution
  torch::Tensor mask_r = torch::rand_like(probs_r) < probs_r;
  torch::Tensor R = torch::zeros_like(B);
  R.masked_scatter_(mask_r, B.masked_select(mask_r) / probs_r.masked_select(mask_r));

  return torch::matmul(S, R);
}
}
