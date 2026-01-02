//
// Created by haolan on 6/5/23.
//
#include <MatrixLoader/CCAMatrixLoader.h>
#include <Utils/IntelliLog.h>
#include <LibAMM.h>
#include <fstream>
#include <iostream>

void LibAMM::CCAMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
}

void LibAMM::CCAMatrixLoader::generateAB() {
  INTELLI_INFO("This function is not used");
}

//do nothing in abstract class
bool LibAMM::CCAMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::CCAMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::CCAMatrixLoader::getB() {
  return B;
}

torch::Tensor LibAMM::CCAMatrixLoader::getAt() {
  return At;
}

torch::Tensor LibAMM::CCAMatrixLoader::getBt() {
  return Bt;
}

torch::Tensor LibAMM::CCAMatrixLoader::getSxx() {
  return Sxx;
}

torch::Tensor LibAMM::CCAMatrixLoader::getSyy() {
  return Syy;
}

torch::Tensor LibAMM::CCAMatrixLoader::getSxy() {
  return Sxy;
}

torch::Tensor LibAMM::CCAMatrixLoader::getSxxNegativeHalf() {
  return SxxNegativeHalf;
}

torch::Tensor LibAMM::CCAMatrixLoader::getSyyNegativeHalf() {
  return SyyNegativeHalf;
}

torch::Tensor LibAMM::CCAMatrixLoader::getM() {
  return M;
}

torch::Tensor LibAMM::CCAMatrixLoader::getM1() {
  return M1;
}

torch::Tensor LibAMM::CCAMatrixLoader::getCorrelation() {
  return correlation;
}

void LibAMM::CCAMatrixLoader::calculate_correlation() {

  // Sxx, Syy, Sxy: covariance matrix
  Sxx = torch::matmul(A, At) / A.size(1); // 120*120
  Syy = torch::matmul(B, Bt) / A.size(1); // 101*101
  Sxy = torch::matmul(A, Bt) / A.size(1); // 120*101

  // Sxx^(-1/2), Syy^(-1/2), M
  // Sxx^(-1/2) 120*120
  torch::Tensor eigenvaluesSxx, eigenvectorsSxx;
  std::tie(eigenvaluesSxx, eigenvectorsSxx) = at::linalg_eig(Sxx); // diagonization
  torch::Tensor diagonalMatrixSxx = torch::diag(
      1.0 / torch::sqrt(eigenvaluesSxx + torch::full({}, 1e-12))); // 1/sqrt(eigenvalue+epsilon) +epsilon to avoid nan
  SxxNegativeHalf = torch::matmul(torch::matmul(eigenvectorsSxx, diagonalMatrixSxx), eigenvectorsSxx.t());
  SxxNegativeHalf = at::real(SxxNegativeHalf); // ignore complex part, it comes from numerical computations
  // Syy^(-1/2) 101*101
  torch::Tensor eigenvaluesSyy, eigenvectorsSyy;
  std::tie(eigenvaluesSyy, eigenvectorsSyy) = at::linalg_eig(Syy);
  torch::Tensor diagonalMatrixSyy = torch::diag(1.0 / torch::sqrt(eigenvaluesSyy + torch::full({}, 1e-12)));
  SyyNegativeHalf = torch::matmul(torch::matmul(eigenvectorsSyy, diagonalMatrixSyy), eigenvectorsSyy.t());
  SyyNegativeHalf = at::real(SyyNegativeHalf);
  // M 120*101
  M1 = torch::matmul(SxxNegativeHalf.t(), Sxy);
  M = torch::matmul(M1, SyyNegativeHalf);

  // correlation
  torch::Tensor U, S, Vh;
  std::tie(U, S, Vh) = at::linalg_svd(M, false, c10::nullopt);
  correlation = torch::clamp(S, -1.0, 1.0);
}
