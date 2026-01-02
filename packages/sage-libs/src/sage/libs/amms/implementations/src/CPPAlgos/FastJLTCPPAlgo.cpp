//
// Created by luv on 6/18/23.
//

#include <CPPAlgos/FastJLTCPPAlgo.h>

namespace LibAMM {
torch::Tensor hadamard_transform_matrix(int64_t n) {
  torch::Tensor H = torch::ones({1, 1}, torch::kInt8);
  int64_t i = 1;
  while (i < n) {
    auto H_top = torch::cat({H, H}, 1);
    auto H_bottom = torch::cat({H, -H}, 1);
    H = torch::cat({H_top, H_bottom}, 0); // view or shallow copy of H_top and H_bottom
    // std::cout << "i: " << i << " n: " << n << std::endl;
    // size_t H_memory_bytes = H.numel() * H.element_size();
    // double H_memory_gigabytes = static_cast<double>(H_memory_bytes) / (1024 * 1024 * 1024);
    // std::cout << "Memory used by the H: " << H_memory_gigabytes << " GB" << std::endl;
    i *= 2;
  }
  return H;
}

torch::Tensor FastJLTCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t d_) {
  int64_t d = (int64_t) d_;
  int64_t N = A.size(0);
  int64_t D = A.size(1);
  int64_t M = B.size(1);

  // Pad A and B for FHT
  int64_t log2_D = std::ceil(std::log2(static_cast<float>(D)));
  int64_t D_pad = static_cast<int64_t>(std::pow(2, log2_D));
  torch::Tensor A_pad = torch::zeros({N, D_pad});
  A_pad.narrow(1, 0, D) = A;
  torch::Tensor B_pad = torch::zeros({D_pad, M});
  B_pad.narrow(0, 0, D) = B;

  // Construct and apply random signs for each dimension
  torch::Tensor randsigns = (torch::randint(0, 2, {D_pad}) * 2 - 1).to(torch::kFloat32);
  randsigns *= 1.0 / std::sqrt(static_cast<float>(D_pad));
  A_pad *= randsigns;
  B_pad *= randsigns.view({-1, 1});

  // Apply Fast Hadamard Transform
  // for MNIST, A columns=60000, that means H dimension=65536*65536, which is too big for silver(32G) to perform the following computation. Thus we comment out below and do it in batch
  torch::Tensor H = hadamard_transform_matrix(D_pad);
  // A_pad = torch::matmul(A_pad, H.t());
  // B_pad = torch::matmul(H, B_pad);
  // batch process below achieves the same as above
  int64_t chunk_size = 10000;
  int64_t num_chunks = (D_pad + chunk_size - 1) / chunk_size;
  torch::Tensor A_pad_result = torch::zeros({A_pad.size(0), A_pad.size(1)});
  for (int64_t i = 0; i < num_chunks; ++i) {
    int64_t start_idx = i * chunk_size;
    int64_t end_idx = std::min((i + 1) * chunk_size, D_pad);
    // std::cout << i << " s: " << start_idx << " e: " << end_idx << std::endl;
    A_pad_result.narrow(1, start_idx, end_idx - start_idx) = torch::matmul(A_pad, H.slice(0, start_idx, end_idx).t().to(torch::kFloat32));
  }
  A_pad = A_pad_result;
  torch::Tensor B_pad_result = torch::zeros({B_pad.size(0), B_pad.size(1)});
  for (int64_t i = 0; i < num_chunks; ++i) {
    int64_t start_idx = i * chunk_size;
    int64_t end_idx = std::min((i + 1) * chunk_size, D_pad);
    B_pad_result.narrow(0, start_idx, end_idx - start_idx) = torch::matmul(H.slice(0, start_idx, end_idx).to(torch::kFloat32), B_pad);
  }
  B_pad = B_pad_result;

  // Dimensionality reduction
  float q = static_cast<float>(log2_D * log2_D) / static_cast<float>(D_pad);
  auto mask = torch::rand({d, D_pad});
  mask = (mask < q).to(torch::kFloat32); // 1 with probability q, 0 with probability 1-q
  auto normal_dist_tensor = torch::randn({d, D_pad}) * std::sqrt(1.0 / q);
  auto P = mask * normal_dist_tensor / std::sqrt(static_cast<float>(d));
  return torch::matmul(torch::matmul(A_pad, P.t()), torch::matmul(P, B_pad));
  // torch::Tensor probs = torch::ones(D_pad) / D_pad;  // default: uniform
  // torch::Tensor indices = torch::multinomial(probs, d, true);
  // torch::Tensor A_sampled = A_pad.t().index_select(0, indices);
  // A_sampled = (A_sampled / (int) d).t().div(torch::ones(1) / D_pad);
  // torch::Tensor B_sampled = B_pad.index_select(0, indices);
  // return torch::matmul(A_sampled, B_sampled);
}
} // LibAMM
