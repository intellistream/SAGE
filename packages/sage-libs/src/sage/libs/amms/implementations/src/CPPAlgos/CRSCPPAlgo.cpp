//
// Created by tony on 25/05/23.
//

#include <CPPAlgos/CRSCPPAlgo.h>
#include <Utils/UtilityFunctions.h>
#include <chrono>
namespace LibAMM {
torch::Tensor LibAMM::CRSCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t k) {
  torch::Tensor C;
  auto start = std::chrono::high_resolution_clock::now();



  // Sample k rows from B

  if (useCuda) {
    INTELLI_INFO("CRS under cuda!");
    // Probability distribution
    int64_t n = A.size(0);
    torch::Tensor probs = torch::ones(n) / n;  // default: uniform
    probs=probs.to(torch::kCUDA);
    A = A.to(torch::kCUDA);
    B = B.to(torch::kCUDA);
    buildATime = chronoElapsedTime(start);
    torch::Tensor B_sampled;
    A = A.t();
    // Sample k indices from range 0 to n for given probability distribution
    torch::Tensor indices = torch::multinomial(probs, k, true);
    indices=indices.to(torch::kCUDA);
    // Sample k columns from A
    torch::Tensor A_sampled = A.index_select(0, indices);
    // int64_t ratio = std::ceil(static_cast<double>(n) / k);
    // A_sampled = (A_sampled / (int) k).t().div(probs.index_select(0, torch::arange(0, n, ratio)));
    A_sampled = (A_sampled / (int) k).t().div(torch::ones(1,torch::kCUDA) / n);

    auto ac = A_sampled.to(torch::kCUDA);

    B_sampled = B.index_select(0, indices);
    auto bc = B_sampled.to(torch::kCUDA);
    buildBTime = chronoElapsedTime(start) - buildATime;
    auto cc = torch::matmul(ac, bc);
    fABTime = chronoElapsedTime(start) - buildATime - buildBTime;
    C = cc.to(torch::kCPU);
    postProcessTime = chronoElapsedTime(start) - buildATime - buildBTime - fABTime;
  } else {
    torch::Tensor B_sampled;
    A = A.t();
    //INTELLI_INFO("I am CPP-CRS");
    int64_t n = A.size(0);
    //int64_t m = A.size(1);

    assert(n == B.size(0));
    // Probability distribution
    torch::Tensor probs = torch::ones(n) / n;  // default: uniform

    // Sample k indices from range 0 to n for given probability distribution
    torch::Tensor indices = torch::multinomial(probs, k, true);

    // Sample k columns from A
    torch::Tensor A_sampled = A.index_select(0, indices);
    // int64_t ratio = std::ceil(static_cast<double>(n) / k);
    // A_sampled = (A_sampled / (int) k).t().div(probs.index_select(0, torch::arange(0, n, ratio)));
    A_sampled = (A_sampled / (int) k).t().div(torch::ones(1) / n);
    buildATime = chronoElapsedTime(start);
    B_sampled = B.index_select(0, indices);
    buildBTime = chronoElapsedTime(start) - buildATime;
    C = torch::matmul(A_sampled, B_sampled);
    fABTime = chronoElapsedTime(start) - buildATime - buildBTime;
  }
  return C;
}
} // LibAMM
