//
// Created by tony on 25/05/23.
//

#include <CPPAlgos/WeightedCRCPPAlgo.h>
#include <ATen/ATen.h>

namespace LibAMM {
torch::Tensor LibAMM::WeightedCRCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t c) {

  int64_t n = A.size(1); // A: m*n, B: n*d
  // std::cout << "A shape: " << A.sizes() << std::endl;
  // std::cout << "B shape: " << B.sizes() << std::endl;

  // Probability distribution
  torch::Tensor col_norm_A = torch::norm(A, /*p=*/2, /*dim=*/0); // norm on columns of A
  torch::Tensor row_norm_B = torch::norm(B, /*p=*/2, /*dim=*/1); // norm on rows of B
  torch::Tensor probability_distribution = torch::mul(col_norm_A, row_norm_B);
  probability_distribution /= probability_distribution.sum();
  // torch::Tensor probability_distribution = torch::ones(n) / n;

  // unique indices and occurences
  torch::manual_seed(999);
  torch::Tensor sample_indices = torch::multinomial(probability_distribution, /*num_samples*/c, /*replacement*/true);

  torch::Tensor unique_indices, _, occurences;
  std::tie(unique_indices, _, occurences) =
      at::_unique2(sample_indices, /*sorted*/false, /*return_inverse*/false, /*return_counts*/true);

  // sample with occurences as weight
  torch::Tensor At_sampled = A.t().index_select(0, unique_indices);
  torch::Tensor A_sampled = At_sampled.t() * occurences / (int) c * n;
  torch::Tensor B_sampled = B.index_select(0, unique_indices);
  torch::Tensor weighted_CR = torch::matmul(A_sampled, B_sampled);

  return weighted_CR;
}
} // LibAMM
