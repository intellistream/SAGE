//
// Created by haolan on 25/6/23.
//
#include <CPPAlgos/ProductQuantizationHash.h>

void LibAMM::ProductQuantizationHash::setConfig(INTELLI::ConfigMapPtr cfg) {
    C = cfg->tryU64("C", 10, true);
    prototypesLoadPath = cfg->tryString("prototypesLoadPath", "torchscripts/PQ/prototypes.pt", true);
    hashLoadPath = cfg->tryString("hashLoadPath", "torchscripts/PQ/hash.pt", true);
    }

int compute_hash_bucket(const std::vector<int>& split_indices, const std::vector<torch::Tensor>& split_thresholds, const torch::Tensor& x) {
    int i = 0;
    for (int t = 0; t < 4; t++) {
        int j_t = split_indices[t];
        torch::Tensor v_t = split_thresholds[t];
        float v = v_t[0][i].item<float>();
        int b = (x[j_t].item<float>() >= v) ? 1 : 0;
        i = 2 * i - 1 + b;
    }
    return i;
}

torch::Tensor LibAMM::ProductQuantizationHash::amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize) {

    const int D = A.size(1);
    sketchSize=0; // no need this parameter
    const int D_c = D / C;

    INTELLI_INFO("Load prototypes from " + prototypesLoadPath);
    torch::Tensor prototypes;
    torch::serialize::InputArchive archive;
    // archive.load_from("/home/yuhao/Documents/work/SUTD/AMM/codespace/LibAMM/benchmark/torchscripts/PQ/prototypes_PCA_SIFT_Small_A_minus_mean.pt");
    archive.load_from(prototypesLoadPath);
    archive.read("prototypes", prototypes);

    INTELLI_INFO("Load hash from " + hashLoadPath);
    // torch::jit::script::Module container = torch::jit::load("/home/yuhao/Documents/work/SUTD/AMM/codespace/LibAMM/yuhao/container.pt");
    torch::jit::script::Module container = torch::jit::load(hashLoadPath);

    torch::Tensor split_indices_tensor = container.attr("split_indices").toTensor();
    std::vector<int> split_indices(split_indices_tensor.data_ptr<int>(), split_indices_tensor.data_ptr<int>() + split_indices_tensor.numel());
    torch::Tensor v1 = container.attr("v1").toTensor();
    torch::Tensor v2 = container.attr("v2").toTensor();
    torch::Tensor v3 = container.attr("v3").toTensor();
    torch::Tensor v4 = container.attr("v4").toTensor();
    std::vector<torch::Tensor> split_thresholds = {v1, v2, v3, v4};
    std::vector<torch::Tensor> A_encoded;

  for (int i = 0; i < A.size(0); ++i) {
    torch::Tensor a = A[i];
    std::vector<torch::Tensor> a_encoded;
    for (int c = 0; c < C; ++c) {
      //auto prototypes_c = prototypes[c];
      auto a_subvector = a.slice(0, c * D_c, (c + 1) * D_c);

      auto closest_prototype_index = compute_hash_bucket(split_indices, split_thresholds, a_subvector);

      a_encoded.push_back(torch::tensor(closest_prototype_index).unsqueeze(0));
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
