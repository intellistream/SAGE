//
// Created by haolan on 5/30/23.
//
#include <CPPAlgos/BetaCoOFDCPPAlgo.h>

torch::Scalar get_first_element(const torch::Tensor &tensor) {
  if (tensor.numel() == 1) {
    return tensor.item();
  } else {
    return tensor[0].item();
  }
}

bool is_empty_tensor(const torch::Tensor &tensor) {
  return tensor.numel() == 0;
}

namespace LibAMM {
torch::Tensor attenuate(float beta, const torch::Tensor &k, int l) {
  return (torch::exp(k * beta / (l - 1)) - 1) / (torch::exp(torch::tensor(beta)) - 1);
}

torch::Tensor paramerizedReduceRank(const torch::Tensor &SV, float delta, int l, float beta) {
  torch::Tensor indices = torch::arange(l, torch::kFloat32);
  torch::Tensor attenuated_values = attenuate(beta, indices, l);
  torch::Tensor parameterizedReduceRank = delta * attenuated_values;
  torch::Tensor SV_shrunk = torch::clamp(SV - parameterizedReduceRank, 0);
  return SV_shrunk;
}

void LibAMM::BetaCoOFDCPPAlgo::setConfig(INTELLI::ConfigMapPtr cfg) {
  algoBeta = cfg->tryDouble("algoBeta", 1.0, true);
}

torch::Tensor BetaCoOFDCPPAlgo::amm(const torch::Tensor A, const torch::Tensor B, uint64_t l2) {
  torch::Tensor B_t = B.t();
  float beta = algoBeta;
  INTELLI_INFO("BETA-COOCURRING, use beta " + to_string(beta));
  TORCH_CHECK(A.size(1) == B_t.size(1), "Shapes of A and B are incompatible");
  int64_t mx = A.size(0);
  int64_t my = B_t.size(0);
  int64_t n = A.size(1);
  int64_t l = (int64_t) l2;
  // Initialize sketch matrices
  torch::Tensor BX = torch::zeros({mx, l});
  torch::Tensor BY = torch::zeros({my, l});

  // The first l iterations
  for (int64_t i = 0; i < l; ++i) {
    BX.slice(1, i, i + 1) = A.slice(1, i, i + 1);
    BY.slice(1, i, i + 1) = B_t.slice(1, i, i + 1);
  }

  torch::Tensor zero_columns = torch::tensor({0});
  zero_columns = zero_columns.slice(0, 1);

  // Iteration l to n: insert if available, else shrink sketch matrices
  for (int64_t i = l; i < n; ++i) {
    // Acquire the index of a zero-valued column
    if (!is_empty_tensor(zero_columns)) {
      int idx = get_first_element(zero_columns).toInt();
      BX.slice(1, idx, idx + 1) = A.slice(1, i, i + 1);
      BY.slice(1, idx, idx + 1) = B_t.slice(1, i, i + 1);
      zero_columns = zero_columns.slice(0, 1);
    }
      // If no zero-valued column, shrink accordingly
    else {
      torch::Tensor QX, RX;
      std::tie(QX, RX) = at::linalg_qr(BX);
      torch::Tensor QY, RY;
      std::tie(QY, RY) = at::linalg_qr(BY);
      torch::Tensor U, SV, V;
      std::tie(U, SV, V) = torch::svd(torch::matmul(RX, RY.t()));

      // Find the median of singular values
      torch::Tensor S_sorted, S_indices;
      std::tie(S_sorted, S_indices) = SV.sort();

      float delta;
      if (S_sorted.size(0) % 2 == 1) {
        delta = S_sorted[S_sorted.size(0) / 2].item().toFloat();
      } else {
        delta = torch::median(S_sorted).item().toFloat();
      }
      // delta = S_sorted[0].item().toFloat();

      // Shrink the singular values with delta
      torch::Tensor SV_shrunk = paramerizedReduceRank(SV, delta, l, beta);

      // Restore SV diagonal matrix
      SV = torch::diag_embed(SV_shrunk);
      torch::Tensor SV_sqrt = torch::sqrt(SV);

      // Update indices of zero-valued columns
      torch::Tensor zero_indices = torch::nonzero(SV_shrunk == 0).squeeze();
      zero_indices = zero_indices.view({-1});  // Convert to a 1D tensor
      zero_columns = torch::cat({zero_columns, zero_indices});
      // Convert tensor to a std::vector
      std::vector<int64_t>
          vec(zero_columns.data_ptr<int64_t>(), zero_columns.data_ptr<int64_t>() + zero_columns.numel());

      // Sort the vector
      std::sort(vec.begin(), vec.end());

      // Remove duplicates
      vec.erase(std::unique(vec.begin(), vec.end()), vec.end());

      // Convert std::vector back to a tensor
      zero_columns = torch::from_blob(vec.data(), {static_cast<int64_t>(vec.size())}, torch::kInt64).clone();

      // Update sketch matrices
      BX = torch::matmul(torch::matmul(QX, U), SV_sqrt);
      BY = torch::matmul(torch::matmul(QY, V), SV_sqrt);
    }
  }

  return torch::matmul(BX, BY.t());
}
}
