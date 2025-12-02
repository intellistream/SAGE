//
// Created by Isshin on 2024/1/8.
//
#include <PQIndex/Clustering.h>
#include <faiss/utils/random.h>
#include <faiss/utils/utils.h>
#include <iostream>
/*
bool CANDY::Clustering::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  vecDim_ = cfg->tryI64("vecDim", 768, true);
  k_ = cfg->tryI64("ANNK", 256, true);
  centroids_ = torch::rand({k_, vecDim_});
  return true;
}*/

void CANDY::Clustering::reset() {
  centroids_ = torch::zeros({k_, vecDim_});
}

auto CANDY::Clustering::getCentroids() -> torch::Tensor {
  return centroids_;
}

double CANDY::Clustering::imbalance_factor(size_t n, int64_t k, int64_t *assign) {
  std::vector<int> hist(k, 0);
  for (size_t i = 0; i < n; i++) {
    hist[assign[i]]++;
  }
  double imbalanced_fac = 0, sum = 0;
  for (int64_t i = 0; i < k; i++) {
    sum += hist[i];
    imbalanced_fac += hist[i] * (double) hist[i];
  }
  imbalanced_fac = imbalanced_fac * k / (sum * sum);
  return imbalanced_fac;
}

void CANDY::Clustering::train(size_t nx,
                              const torch::Tensor x_in,
                              faiss::IndexFlatL2 *index,
                              const torch::Tensor *weights) {

  int64_t assign[nx];
  float dis[nx];
  size_t n_input_centroids = 0;
  //remember best iteration
  torch::Tensor best_centroids;
  float best_obj = HUGE_VALF;
  std::vector<ClusteringIterationStats> best_iteration_stats;
  double t_search_tot = 0;

  double t0 = faiss::getmillisecs();

  for (int redo = 0; redo < nredo; redo++) {
    // initialize centroids with random points from x_in
    std::vector<int> perm(nx);
    faiss::rand_perm(perm.data(), nx, 1919810);
    for (int i = n_input_centroids; i < k_; i++) {

      centroids_.slice(0, i, i + 1) = x_in.slice(0, perm[i], perm[i] + 1);

    }

    if (index->ntotal != 0) {
      index->reset();
    }

    float *centroids_data = centroids_.contiguous().data_ptr<float>();
    if (!index->is_trained) {
      index->train(k_, centroids_data);
    }
    index->add(k_, centroids_data);
    // k-means iteration
    float obj = 0;
    for (int i = 0; i < niter; i++) {
      double t0s = faiss::getmillisecs();
      float *x_in_data = x_in.contiguous().data_ptr<float>();
      index->search(nx, x_in_data, 1, dis, assign);

      t_search_tot += faiss::getmillisecs() - t0s;
      // accumulate objective
      obj = 0;
      for (size_t j = 0; j < nx; j++) {
        obj = obj + dis[j];
      }

      torch::Tensor hassign = torch::zeros({k_});
      size_t k_frozen = 0;

      computeCentroids(vecDim_, k_, nx, k_frozen, x_in, assign, weights, &hassign, &centroids_);
      int n_split = splitClusters(vecDim_, k_, nx, k_frozen, &hassign, &centroids_);
      ClusteringIterationStats stats = {
          obj,
          (faiss::getmillisecs() - t0) / 1000.0,
          t_search_tot / 1000,
          n_split
      };
      iteration_stats_.push_back(stats);
      if (update_index) {
        centroids_data = centroids_.contiguous().data_ptr<float>();
        index->train(k_, centroids_data);
      }
      index->add(k_, centroids_data);
    }

    if (nredo > 1) {
      if (obj < best_obj) {
        best_centroids = centroids_;
        best_iteration_stats = iteration_stats_;
        best_obj = obj;
      }
      index->reset();
    }
  }
  if (nredo > 1) {
    centroids_ = best_centroids;
    iteration_stats_ = best_iteration_stats;
    index->reset();
    float *best_centroids_data = centroids_.contiguous().data_ptr<float>();
    index->add(k_, best_centroids_data);
  }
}

void CANDY::Clustering::computeCentroids(
    int64_t d,
    int64_t k,
    size_t n,
    int64_t k_frozen,
    const torch::Tensor x_in,
    const int64_t *assign,
    const torch::Tensor *weights,
    torch::Tensor *hassign,
    torch::Tensor *centroids
) {
  // Only deal with centroids[k_:]
  for (int64_t i = k_frozen; i < k; i++) {
    centroids_[i] = torch::zeros({vecDim_});
  }

  // Single Thread version : the only thread responsible for all centroids;
  for (size_t i = 0; i < n; i++) {
    auto ci = assign[i];

    if (ci >= k_) {
      continue;
    }
    if (ci < k_frozen) {
      continue;
    }
    // Update unfrozen centroids;
    auto ci_centroid = (*centroids)[ci];
    auto xi = x_in[i];
    if (weights != nullptr) {
      float weight_i = (*weights)[i].item<float>();
      (*hassign)[ci] = (*hassign)[ci] + weight_i;
      ci_centroid = ci_centroid + weight_i * xi;
      (*centroids)[ci] = ci_centroid;
    } else {
      (*hassign)[ci] += 1.0;
      ci_centroid = ci_centroid + xi;
      (*centroids)[ci] = ci_centroid;
    }

  }

  //normalize unfrozen centroids
  for (faiss::idx_t ci = k_frozen; ci < k_; ci++) {
    float norm = 1 / ((*hassign)[ci].item<float>());
    (*centroids)[ci] = (*centroids)[ci] * norm;
  }

}
//TODO: FIX RNG PROB AND hassign
#define EPSILON (1/1024.0)
int CANDY::Clustering::splitClusters(int64_t d,
                                     int64_t k,
                                     size_t n,
                                     int64_t k_frozen,
                                     torch::Tensor *hassign,
                                     torch::Tensor *centroids) {
  size_t nsplit = 0;
  faiss::RandomGenerator rng(1919810);
  for (int64_t ci = k_frozen; ci < k_; ci++) {
    // need to redefine centroid for this one
    if ((*hassign)[ci].item<float>() == 0) {
      // to find the centroid to split
      size_t cj;
      for (cj = 0; true; cj = (cj + 1) % k) {
        float p = ((*hassign)[cj].item<float>() - 1) / (float) (n - k);
        float r = rng.rand_float();
        if (r < p) {
          break; // centroid found to split
        }
      }
      // copy cj to ci
      (*centroids)[ci] = (*centroids)[cj];

      for (int64_t j = 0; j < d; j++) {
        if (j % 2 == 0) {
          (*centroids)[ci][j] *= (1 + EPSILON);
          (*centroids)[cj][j] *= (1 - EPSILON);
        } else {
          (*centroids)[ci][j] *= (1 - EPSILON);
          (*centroids)[cj][j] *= (1 + EPSILON);
        }
      }

      (*hassign)[ci] = (*hassign)[cj] / 2;
      (*hassign)[cj] -= (*hassign)[ci];
      nsplit++;
    }
  }
  return nsplit;
}
