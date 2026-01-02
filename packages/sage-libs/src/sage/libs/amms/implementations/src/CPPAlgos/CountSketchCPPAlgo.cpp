//
// Created by haolan on 5/26/23.
//

#include <CPPAlgos/CountSketchCPPAlgo.h>

namespace LibAMM {
torch::Tensor LibAMM::CountSketchCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t k2) {
  int64_t m1 = A.size(0);
  int64_t n = A.size(1);
  int64_t m2 = B.size(1);
  int64_t k = (int64_t) k2;
  // Initialize sketch matrices
  torch::Tensor Ca = torch::zeros({m1, k});
  torch::Tensor Cb = torch::zeros({k, m2});

  torch::Tensor L = torch::randint(k, {n});
  torch::Tensor G = torch::randint(2, {n});

  // Modify the random column with random sign
  for (int64_t i = 0; i < n; ++i) {
    if (G[i].item<int>() == 1) {
      Ca.index({torch::indexing::Slice(), L[i]}).add_(A.index({torch::indexing::Slice(), i}));
      Cb.index({L[i], torch::indexing::Slice()}).add_(B.index({i, torch::indexing::Slice()}));
    } else {
      Ca.index({torch::indexing::Slice(), L[i]}).sub_(A.index({torch::indexing::Slice(), i}));
      Cb.index({L[i], torch::indexing::Slice()}).sub_(B.index({i, torch::indexing::Slice()}));
    }
  }

  return torch::matmul(Ca, Cb);
}
} // LibAMM
