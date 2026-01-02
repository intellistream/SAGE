//
// Created by luv on 5/30/23.
//

#include <CPPAlgos/TugOfWarCPPAlgo.h>

namespace LibAMM {
void TugOfWarCPPAlgo::setConfig(INTELLI::ConfigMapPtr cfg) {
  algoDelta = cfg->tryDouble("algoDelta", algoDelta, true);
}

torch::Tensor TugOfWarCPPAlgo::generateTugOfWarMatrix(int64_t m, int64_t n) {
  torch::Tensor matrix = torch::empty({m, n}, torch::kFloat32);
  torch::randn_out(matrix, {m, n});
  matrix.sign_();
  matrix = matrix/float(std::sqrt(m));
  return matrix;
}

torch::Tensor TugOfWarCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t l2) {
  int64_t n = A.size(1);
  int64_t p = B.size(1);
  int64_t l = (int64_t) l2;

  double delta = algoDelta;

  int64_t i_iters = static_cast<int64_t>(-std::log(delta));
  int64_t j_iters = static_cast<int64_t>(2 * (-std::log(delta) + std::log(-std::log(delta))));

  torch::Tensor z = torch::empty({i_iters});
  std::vector<torch::Tensor> AS;
  std::vector<torch::Tensor> SB;

  for (int64_t i = 0; i < i_iters; ++i) {
    torch::Tensor S = generateTugOfWarMatrix(l, n);
    SB.push_back(S.matmul(B));
    AS.push_back(A.matmul(S.t()));

    torch::Tensor y = torch::empty({j_iters});

    for (int64_t j = 0; j < j_iters; ++j) {
      torch::Tensor Q = generateTugOfWarMatrix(16, p);
      torch::Tensor X = A.matmul(B.matmul(Q.t()));
      torch::Tensor X_hat = AS[i].matmul(SB[i].matmul(Q.t()));
      y[j] = torch::norm(X - X_hat).pow(2);
    }

    z[i] = at::median(y);
  }

  torch::Tensor z_argmin = z.argmin();
  int64_t i_star = z_argmin.item<int64_t>();

  return AS[i_star].matmul(SB[i_star]);
}
} // LibAMM
