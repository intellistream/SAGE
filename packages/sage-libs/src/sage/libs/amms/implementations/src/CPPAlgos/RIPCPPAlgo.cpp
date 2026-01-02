//
// Created by tony on 25/05/23.
//

#include <CPPAlgos/RIPCPPAlgo.h>
#include <LibAMM.h>

using namespace std;
using namespace INTELLI;
using namespace torch;

torch::Tensor createRandomTensor(int N) {
  // return a tensor
  torch::Tensor tensor = torch::empty(N);
  tensor.uniform_(-1, 1); // Fill the tensor with values uniformly sampled from [-1, 1]
  tensor.sign_(); // Set the sign of each element to either 1 or -1

  return tensor;
}

namespace LibAMM {
torch::Tensor LibAMM::RIPCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t k2) {

  // Step 1: Input A:n1*d B:d*n2
  A = A.t(); // d*n1
  int64_t d = A.size(0);
  int64_t k = (int64_t) k2;

  // Step 2: RIP matrix k*d
  torch::Tensor RIP = torch::zeros({k, d});

  // first row as Rademacher random vector, X=+1 w.p. 1/2, X=-1 w.p. 1/2 1*d
  // torch::Tensor firstRow = 1 / std::sqrt(k) * createRandomTensor(d);

  // from paper: each subsequent row is created by rotating one element to the right relative to the preceding row vector d*d, then sample k rows from d*d, get RIP matrix k*d
  // in implementation, we create k*d directly to avoid create such a big matrix d*d
  // torch::Tensor indices = torch::multinomial(torch::ones(d) / d, k, /*replacement*/false);
  // for (int64_t i = 0; i < k; ++i) {
  //   INTELLI_INFO(to_string(i) + "/" + to_string(k));
  //   RIP[i] = torch::roll(firstRow, indices[i].item<int>());
  // }
  // we comment above for flat matrix A, cuz roll operation too expensive
  RIP = torch::empty({k, d});
  RIP.uniform_(-1, 1);
  RIP.sign_();
  RIP = RIP * 1 / std::sqrt(k);

  // Step 3: Randomized column signs
  torch::Tensor D = createRandomTensor(d);

  // Step 4: Compute AVVTB
  torch::Tensor A_prime = torch::matmul(RIP, A*D.view({-1, 1})); // A' = k*d * d*n1 = k*n1
  torch::Tensor B_prime = torch::matmul(RIP, B*D.view({-1, 1})); // B' = k*d * d*n2 = k*n2
  return torch::matmul(A_prime.t(), B_prime);
}
} // LibAMM

// GDB debug purpose
// int main() {
//     // torch::manual_seed(114513);
//     LibAMM::RIPCPPAlgo rip;
//     auto A = torch::rand({600, 400});
//     auto B = torch::rand({400, 1000});
//     auto realC = torch::matmul(A, B);
//     auto ammC = rip.amm(A, B, 20);
//     double froError = INTELLI::UtilityFunctions::relativeFrobeniusNorm(realC, ammC);
//     std::cout << froError << std::endl;
//     // REQUIRE(froError < 0.5);
// }
