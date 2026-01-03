//
// Created by tony on 10/05/23.
//

#include <MatrixLoader/SparseMatrixLoader.h>
#include <Utils/IntelliLog.h>
#include <vector>
#include <random>

torch::Tensor LibAMM::SparseMatrixLoader::genSparseMatrix(uint64_t m,
                                                            uint64_t n,
                                                            double density,
                                                            uint64_t reduceRows) {
  /**
   * @brief 1. gen random mat
   */
  auto mat = torch::rand({(long) m, (long) n});

  // Iterate over each element of A and zero out the element with probability p
  /**
   * @brief 2. make it sparse according to density
   */
  if (density < 1.0) {
    for (uint64_t i = 0; i < m; i++) {
      for (uint64_t j = 0; j < n; j++) {
        if (torch::rand({1}).item<float>() >= density) {
          mat[i][j] = 0.0;
        }
      }
    }
  }

  /**
   * @brief 3. reduce rows
   */
  if (reduceRows == 0) {
    return mat;
  }

  std::vector<uint64_t> selected_rows(reduceRows);
  std::iota(selected_rows.begin(), selected_rows.end(), 0);
  for (uint64_t i = reduceRows; i < m; ++i) {
    uint64_t j = std::rand() % (i + 1);
    if (j < reduceRows) {
      selected_rows[j] = i;
    }
  }
  for (const uint64_t &row_idx : selected_rows) {
    //mat[row_idx]=mat[0]*torch::rand({1}).item<float>();
    mat[row_idx] = mat[0];
    // do something with the row, e.g. print it
    //std::cout << row_idx << std::endl;

  }
  return mat;
}

void LibAMM::SparseMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  aRow = cfg->tryU64("aRow", 100, true);
  aCol = cfg->tryU64("aCol", 1000, true);
  bCol = cfg->tryU64("bCol", 500, true);
  seed = cfg->tryU64("seed", 114514, true);
  aDensity = cfg->tryDouble("aDensity", 1.0, true);
  bDensity = cfg->tryDouble("bDensity", 1.0, true);
  aReduce = cfg->tryU64("aReduce", 0, true);
  bReduce = cfg->tryU64("bReduce", 0, true);
  if (aReduce >= aRow) {
    aReduce = aRow - 1;
  }
  if (bReduce >= aCol) {
    aReduce = aCol - 1;
  }
  INTELLI_INFO(
      "Generating [" + to_string(aRow) + "x" + to_string(aCol) + "]*[" + to_string(aCol) + "x" + to_string(bCol)
          + "], please wait for a while");
}

void LibAMM::SparseMatrixLoader::generateAB() {
  torch::manual_seed(seed);
  std::srand(seed);
  A = genSparseMatrix(aRow, aCol, aDensity, aReduce);
  INTELLI_INFO(
      "Sparse matrix A is done");
  B = genSparseMatrix(aCol, bCol, bDensity, bReduce);
  INTELLI_INFO(
      "Sparse matrix B is done");
}

//do nothing in abstract class
bool LibAMM::SparseMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::SparseMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::SparseMatrixLoader::getB() {
  return B;
}
