//
// Created by yuhao on 6/6/23.
//

#include <CPPAlgos/SMPPCACPPAlgo.h>
#include <Utils/UtilityFunctions.h>
#include <chrono>
namespace LibAMM {
torch::Tensor LibAMM::SMPPCACPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t k2) {
  if(useCuda) {
    INTELLI_INFO("I am SMP-PCA, using cuda");
  }
  auto start = std::chrono::high_resolution_clock::now();
  if (useCuda) {
    A = A.to(torch::kCUDA);
    buildATime = chronoElapsedTime(start);
    B= B.to(torch::kCUDA);
    buildBTime = chronoElapsedTime(start) - buildATime;
  }
  // Step 1: Input A:n1*d B:d*n2
  A = A.t(); // d*n1
  int64_t d = A.size(0);
  int64_t n1 = A.size(1);
  int64_t n2 = B.size(1);
  int64_t k = (int64_t) k2;

  // Step 2: Get sketched matrix
  torch::Tensor pi = 1 / std::sqrt(k) * torch::randn({k, d}); // Gaussian sketching matrix
  if (useCuda) {
   pi=pi.to(torch::kCUDA);
  }
  torch::Tensor A_tilde = torch::matmul(pi, A); // k*n1
  torch::Tensor B_tilde = torch::matmul(pi, B); // k*n2

  torch::Tensor A_tilde_B_tilde = torch::matmul(A_tilde.t(), B_tilde);

  // Step 3: Compute column norms
  // 3.1 column norms of A and B
  torch::Tensor col_norm_A = at::linalg_vector_norm(A, 2, {0}, false, c10::nullopt); // ||Ai|| for i in [n1]
  torch::Tensor col_norm_B = at::linalg_vector_norm(B, 2, {0}, false, c10::nullopt); // ||Bj|| for j in [n2]

  // 3.2 column norms of A_tilde and B_tilde
  torch::Tensor col_norm_A_tilde = at::linalg_vector_norm(A_tilde, 2, {0}, false,
                                                          c10::nullopt); // ||Ai|| for i in [n1]
  torch::Tensor col_norm_B_tilde = at::linalg_vector_norm(B_tilde, 2, {0}, false,
                                                          c10::nullopt); // ||Bj|| for j in [n2]

  // Step 4: Compute M_tilde
  torch::Tensor col_norm_A_col_norm_B = torch::matmul(col_norm_A.reshape({n1, 1}), col_norm_B.reshape({1, n2}));

  torch::Tensor col_norm_A_tilde_col_norm_B_tilde =
      torch::matmul(col_norm_A_tilde.reshape({n1, 1}), col_norm_B_tilde.reshape({1, n2}));
  torch::Tensor mask = (col_norm_A_tilde_col_norm_B_tilde == 0);
  col_norm_A_tilde_col_norm_B_tilde.masked_fill_(mask, 1e-6); // incase divide by 0 in next step

  torch::Tensor ratio = torch::div(col_norm_A_col_norm_B, col_norm_A_tilde_col_norm_B_tilde);

  torch::Tensor M_tilde = torch::mul(A_tilde_B_tilde, ratio);
  if (useCuda) {
    fABTime = chronoElapsedTime(start) - buildATime - buildBTime;
    M_tilde = M_tilde.to(torch::kCPU);
    postProcessTime=chronoElapsedTime(start)-buildATime-buildBTime-fABTime;
  }
  else {
    fABTime = chronoElapsedTime(start);
  }
  return M_tilde;
}
} // LibAMM
