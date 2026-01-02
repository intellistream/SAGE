//
// Created by tony on 25/05/23.
//

#include <CPPAlgos/BlockLRACPPAlgo.h>
#include <ATen/ATen.h>
#include <vector>
#include <LibAMM.h>
#include <cassert>
using namespace std;

namespace LibAMM {
void LibAMM::BlockLRACPPAlgo::setConfig(INTELLI::ConfigMapPtr cfg) {
  ARankRatio = cfg->tryDouble("algoARankRatio", 0.1, true); // 0.1 is kinda same as sketch_size=0.1
  BRankRatio = cfg->tryDouble("algoBRankRatio", 0.1, true); // 0.1 is kinda same as sketch_size=0.1
}

torch::Tensor LibAMM::BlockLRACPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t l) {

  l=0; // l is meaningless, as "sketch_size" is already set in rank, and blockSize is not about sketch size also.
  uint64_t blockSize = 30;

  // Input size and block size, add 0 means before padding
  uint64_t m0 = A.size(0);
  uint64_t k0 = A.size(1);
  uint64_t n0 = B.size(1);

  // after padding, m0->m, k0->k, n0->n
  uint64_t m = (A.size(0)+(blockSize-1))/blockSize*blockSize;
  uint64_t k = (A.size(1)+(blockSize-1))/blockSize*blockSize;
  uint64_t n = (B.size(1)+(blockSize-1))/blockSize*blockSize;

  // Pad the matrix with zeros
  torch::Tensor padded_A = torch::zeros({(int)m, (int)k});
  padded_A.slice(0, 0, m0).slice(1, 0, k0) = A;
  A = padded_A;
  torch::Tensor padded_B = torch::zeros({(int)k, (int)n});
  padded_B.slice(0, 0, k0).slice(1, 0, n0) = B;
  B = padded_B;

  // for each block, calculate LRA
  torch::Tensor finalLRA = torch::zeros({(long) m, (long) n});

  std::vector<std::vector<std::tuple<torch::Tensor, torch::Tensor, torch::Tensor>>> svdA_blocks(m / blockSize, std::vector<std::tuple<torch::Tensor, torch::Tensor, torch::Tensor>>(k / blockSize));

  std::vector<std::vector<std::tuple<torch::Tensor, torch::Tensor, torch::Tensor>>> svdB_blocks(k / blockSize, std::vector<std::tuple<torch::Tensor, torch::Tensor, torch::Tensor>>(n / blockSize));

  for (uint64_t I = 0; I < m / blockSize; ++I) {
      for (uint64_t K = 0; K < k / blockSize; ++K) {
          torch::Tensor AIK = A.index({torch::indexing::Slice(I * blockSize, (I + 1) * blockSize),
                                        torch::indexing::Slice(K * blockSize, (K + 1) * blockSize)});
          torch::Tensor UA, SA, VhA;
          std::tie(UA, SA, VhA) = at::linalg_svd(AIK, false, c10::nullopt);
          torch::Tensor UATruncated = UA.narrow(1, 0, ceil(ARankRatio * blockSize)); // ceil in case ARankRatio * blockSize < 1, then we set it to 1 at least
          torch::Tensor SATruncated = torch::diag(SA.narrow(0, 0, ceil(ARankRatio * blockSize)));
          torch::Tensor VhATruncated = VhA.narrow(0, 0, ceil(ARankRatio * blockSize));
          svdA_blocks[I][K] = std::make_tuple(UATruncated, SATruncated, VhATruncated);
      }
  }

  for (uint64_t K = 0; K < k / blockSize; ++K) {
      for (uint64_t J = 0; J < n / blockSize; ++J) {
          torch::Tensor BKJ = B.index({torch::indexing::Slice(K * blockSize, (K + 1) * blockSize),
                                        torch::indexing::Slice(J * blockSize, (J + 1) * blockSize)});
          torch::Tensor UB, SB, VhB;
          std::tie(UB, SB, VhB) = at::linalg_svd(BKJ, false, c10::nullopt);
          torch::Tensor UBTruncated = UB.narrow(1, 0, ceil(BRankRatio * blockSize));
          torch::Tensor SBTruncated = torch::diag(SB.narrow(0, 0, ceil(BRankRatio * blockSize)));
          torch::Tensor VhBTruncated = VhB.narrow(0, 0, ceil(BRankRatio * blockSize));
          svdB_blocks[K][J] = std::make_tuple(UBTruncated, SBTruncated, VhBTruncated);
      }
  }

  for (uint64_t I = 0; I < m / blockSize; ++I) {
      for (uint64_t J = 0; J < n / blockSize; ++J) {
          torch::Tensor subFinalLRA = torch::zeros({(long) blockSize, (long) blockSize});
          for (uint64_t K = 0; K < k / blockSize; ++K) {
              const auto& svdA = svdA_blocks[I][K];
              const auto& svdB = svdB_blocks[K][J];
              torch::Tensor UATruncated = std::get<0>(svdA);
              torch::Tensor SATruncated = std::get<1>(svdA);
              torch::Tensor VhATruncated = std::get<2>(svdA);
              torch::Tensor UBTruncated = std::get<0>(svdB);
              torch::Tensor SBTruncated = std::get<1>(svdB);
              torch::Tensor VhBTruncated = std::get<2>(svdB);
              subFinalLRA += torch::matmul(torch::matmul(UATruncated,
                              torch::matmul(torch::matmul(SATruncated,
                                torch::matmul(VhATruncated,UBTruncated)), SBTruncated)), VhBTruncated);
          }

          finalLRA.index_put_({torch::indexing::Slice(I * blockSize, (I + 1) * blockSize),
                              torch::indexing::Slice(J * blockSize, (J + 1) * blockSize)}, subFinalLRA);
      }
  }

  return finalLRA.slice(0,0,m0).slice(1,0,n0);
}}
