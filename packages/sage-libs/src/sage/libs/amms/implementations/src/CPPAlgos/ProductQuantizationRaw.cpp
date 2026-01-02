//
// Created by haolan on 22/6/23.
//
#include <CPPAlgos/ProductQuantizationRaw.h>

void LibAMM::ProductQuantizationRaw::setConfig(INTELLI::ConfigMapPtr cfg) {
    C = cfg->tryU64("C", 10, true);
    prototypesLoadPath = cfg->tryString("prototypesLoadPath", "torchscripts/prototypes.pt", true);
    INTELLI_INFO("prototypesLoadPath: " + prototypesLoadPath);
    }

torch::Tensor LibAMM::ProductQuantizationRaw::amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize) {
  const int D = A.size(1);
  if (sketchSize < 50) C = (int) sketchSize;
  const int D_c = D / C;

  torch::Tensor prototypes;

  torch::serialize::InputArchive archive;
  archive.load_from(prototypesLoadPath);
  archive.read("prototypes", prototypes);

  std::vector<torch::Tensor> A_encoded;

  for (int i = 0; i < A.size(0); ++i) {
    torch::Tensor a = A[i];
    std::vector<torch::Tensor> a_encoded;
    for (int c = 0; c < C; ++c) {
      auto prototypes_c = prototypes[c];
      auto a_subvector = a.slice(0, c * D_c, (c + 1) * D_c);

      auto distances = torch::norm(prototypes_c - a_subvector.expand_as(prototypes_c), 1);
      auto closest_prototype_index = torch::argmin(distances);
      a_encoded.push_back(closest_prototype_index.unsqueeze(0));
    }
    A_encoded.push_back(torch::cat(a_encoded));
  }
  torch::Tensor A_encoded_tensor = torch::stack(A_encoded);

  std::vector<torch::Tensor> tables;

  for (int c = 0; c < C; ++c) {
    auto prototypes_c = prototypes[c];
    auto B_subspace = B.slice(0, c * D_c, (c + 1) * D_c);

    std::vector<torch::Tensor> table_c;
    for (int i = 0; i < prototypes_c.size(0); ++i) {
      auto prototype = prototypes_c[i];
      auto dot_products = prototype.matmul(B_subspace);
      table_c.push_back(dot_products);
    }
    tables.push_back(torch::stack(table_c));
  }

  std::vector<torch::Tensor> result;

  for (int i = 0; i < A_encoded_tensor.size(0); ++i) {
    auto a_encoded = A_encoded_tensor[i];
    auto row_sum = torch::zeros({B.size(1)});
    for (int c = 0; c < C; ++c) {
      int prototype_index = a_encoded[c].item<int>();
      auto table_c = tables[c];
      auto dot_products = table_c[prototype_index];
      row_sum += dot_products;
    }
    result.push_back(row_sum);
  }

  return torch::stack(result);
}
