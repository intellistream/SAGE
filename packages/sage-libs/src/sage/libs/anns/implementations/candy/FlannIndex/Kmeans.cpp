//
// Created by Isshin on 2024/3/23.
//
#include <FlannIndex/Kmeans.h>
bool CANDY::KmeansTree::setConfig(INTELLI::ConfigMapPtr cfg) {

  vecDim = cfg->tryI64("vecDim", 768, true);
  branching = cfg->tryI64("branching", 64, true);

  iterations = cfg->tryI64("iterations", 10, true);
  if (iterations < 0) {
    iterations = (std::numeric_limits<int64_t>::max)();
  }
  cb_index = cfg->tryDouble("cb_index", 0.4, true);

  std::string metricType = cfg->tryString("metricType", "L2", true);
  if (metricType == "dot" || metricType == "IP" || metricType == "cossim") {
    faissMetric = faiss::METRIC_INNER_PRODUCT;
    INTELLI_INFO("USING IP AS METRIC");
  } else {
    faissMetric = faiss::METRIC_L2;
    INTELLI_INFO("USING L2 AS METRIC");
  }

  FlannComponent::setConfig(cfg);
  centerChooser = new FLANN::RandomCenterChooser(&dbTensor, vecDim);
  return true;
}
bool CANDY::KmeansTree::setParams(FlannParam param) {

  branching = param.branching;
  cb_index = param.cb_index;
  iterations = param.maxIterations;
  printf("Best param for Kmeans\n  branching : %ld cb_index: %lf, iterations: %ld\n", branching, cb_index, iterations);
  return true;
}
void CANDY::KmeansTree::addPointToTree(NodePtr node, int64_t idx, float dist) {
  auto data = dbTensor.slice(0, idx, idx + 1);
  auto point_data = data.contiguous().data_ptr<float>();
  // update current node's stat
  if (dist > node->radius) {
    node->radius = dist;
  }
  node->variance = (node->size * node->variance + dist) / (node->size + 1);
  node->size++;

  //leaf node
  if (node->childs.empty()) {
    NodeInfo node_info;
    node_info.index = idx;
    node_info.point = data;
    node->points.push_back(node_info);
    std::vector<int64_t> indices(node->points.size());
    for (size_t i = 0; i < node->points.size(); i++) {
      indices[i] = node->points[i].index;
    }
    computeNodeStat(node, indices);
    if (indices.size() >= (size_t) branching) {

      computeClustering(node, &indices[0], indices.size(), branching);
    }
  } else {
    // find closest child
    int64_t closest = 0;
    float dist = 0;
    if (faissMetric == faiss::METRIC_L2) {
      dist = faiss::fvec_L2sqr(node->childs[closest]->pivot, point_data, vecDim);
    }
    if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
      dist = -faiss::fvec_inner_product(node->childs[closest]->pivot, point_data, vecDim);
    }
    for (int64_t i = 0; i < branching; i++) {
      float cur_dist;
      if (faissMetric == faiss::METRIC_L2) {
        cur_dist = faiss::fvec_L2sqr(node->childs[i]->pivot, point_data, vecDim);
      }
      if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
        cur_dist = -faiss::fvec_inner_product(node->childs[i]->pivot, point_data, vecDim);
      }
      if (cur_dist < dist) {
        dist = cur_dist;
        closest = i;
      }

    }
    // append the new node to the closest child
    addPointToTree(node->childs[closest], idx, dist);
  }
}

void CANDY::KmeansTree::addPoints(torch::Tensor &t) {
  bool success = INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &t, &lastNNZ, expandStep);
  assert(success);
  auto old_size = ntotal;
  ntotal += t.size(0);
  // build from scratch for new tree
  if ((ntotal - t.size(0)) * 2 < ntotal) {
    printf("starting  re-building tree\n");
    if (root) {
      root->~Node();
      root = nullptr;
    }
    std::vector<int64_t> indices(ntotal);
    for (uint64_t i = 0; i < ntotal; i++) {
      indices[i] = i;
    }
    root = new Node();
    computeNodeStat(root, indices);
    computeClustering(root, &indices[0], ntotal, branching);
  } else {
    printf("Adding to existing tree\n");
    // append data incrementally on the trained kmeans-tree
    for (int64_t i = 0; i < t.size(0); i++) {
      auto i_data = dbTensor.slice(0, i, i + 1).contiguous().data_ptr<float>();
      float dist;
      if (faissMetric == faiss::METRIC_L2) {
        dist = faiss::fvec_L2sqr(root->pivot, i_data, vecDim);
      }
      if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
        dist = -faiss::fvec_inner_product(root->pivot, i_data, vecDim);
      }
      addPointToTree(root, old_size + i, dist);
    }
  }
}

void CANDY::KmeansTree::computeNodeStat(NodePtr node, std::vector<int64_t> &indices) {
  auto size = indices.size();
  // compute mean, radius, and variance for the current cluster
  float *mean = new float[vecDim];
  memset(mean, 0, vecDim * sizeof(float));
  for (size_t i = 0; i < size; i++) {
    auto vec = dbTensor.slice(0, indices[i], indices[i] + 1).contiguous().data_ptr<float>();
    for (int64_t j = 0; j < vecDim; j++) {
      mean[j] += vec[j];
    }
  }
  auto div_factor = 1.0 / size;
  for (int64_t j = 0; j < vecDim; j++) {
    mean[j] *= div_factor;
  }
  float radius = 0.0;
  float variance = 0.0;
  for (size_t i = 0; i < size; i++) {
    auto temp = dbTensor.slice(0, indices[i], indices[i] + 1).contiguous().data_ptr<float>();
    float dist;
    if (faissMetric == faiss::METRIC_L2) {
      dist = faiss::fvec_L2sqr(mean, temp, vecDim);
    }
    if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
      dist = -faiss::fvec_inner_product(mean, temp, vecDim);
    }
    if (dist > radius) {
      radius = dist;
    }
    variance += dist;
  }
  variance /= size;

  node->variance = variance;
  node->radius = radius;

  //delete[] node->pivot;
  node->pivot = mean;
}

void CANDY::KmeansTree::computeClustering(NodePtr node, int64_t *indices, int64_t indices_length, int64_t branching) {
  node->size = indices_length;
  // too few nodes for a cluster
  if (indices_length < branching) {
    node->points.resize(branching);
    for (int64_t i = 0; i < indices_length; i++) {
      node->points[i].index = indices[i];
      node->points[i].point = dbTensor.slice(0, indices[i], indices[i] + 1);
    }
    node->childs.clear();
    return;
  }

  // use center chooser to compute the number of nodes within the cluster
  std::vector<int64_t> centers_idx(branching);
  int64_t centers_length;
  (*centerChooser)(branching, indices, indices_length, &centers_idx[0], centers_length);
  if (centers_length < branching) {
    node->points.resize(indices_length);
    for (int64_t i = 0; i < indices_length; ++i) {
      node->points[i].index = indices[i];
      node->points[i].point = dbTensor.slice(0, indices[i], indices[i] + 1);
    }
    node->childs.clear();
    return;
  }
  // init centers with chosen center_idx
  auto centers = new float[branching * vecDim];
  for (int64_t i = 0; i < centers_length; i++) {
    auto vec = dbTensor.slice(0, centers_idx[i], centers_idx[i] + 1).contiguous().data_ptr<float>();
    for (int64_t k = 0; k < vecDim; k++) {
      centers[i * vecDim + k] = (double) vec[k];
    }
  }
  std::vector<float> radiuses(branching, 0);
  std::vector<int> count(branching, 0);

  // assign points to clusters
  std::vector<int64_t> belongs_to(indices_length);
  for (int64_t i = 0; i < indices_length; i++) {
    auto i_vec = dbTensor.slice(0, indices[i], indices[i] + 1).contiguous().data_ptr<float>();
    float sq_dist;
    if (faissMetric == faiss::METRIC_L2) {
      sq_dist = faiss::fvec_L2sqr(i_vec, &centers[0], vecDim);
    }
    if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
      sq_dist = -faiss::fvec_inner_product(i_vec, &centers[0], vecDim);
    }
    belongs_to[i] = 0;
    for (int64_t j = 0; j < branching; j++) {
      float new_dist;
      if (faissMetric == faiss::METRIC_L2) {
        new_dist = faiss::fvec_L2sqr(i_vec, &centers[j * vecDim], vecDim);
      }
      if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
        new_dist = -faiss::fvec_inner_product(i_vec, &centers[j * vecDim], vecDim);
      }
      if (sq_dist > new_dist) {
        belongs_to[i] = j;
        sq_dist = new_dist;
      }
    }
    if (sq_dist > radiuses[belongs_to[i]]) {
      radiuses[belongs_to[i]] = sq_dist;
    }
    count[belongs_to[i]]++;
  }

  bool converged = false;
  int64_t iteration = 0;

  // update cluster iteratively
  while (!converged && iteration < iterations) {
    converged = true;
    iteration++;
    //printf("starting %ld th iteration\n", iteration);

    // compute new cluster center
    for (int64_t i = 0; i < branching; i++) {
      memset(&centers[i * vecDim], 0, sizeof(float) * vecDim);
      radiuses[i] = 0;
    }
    for (int64_t i = 0; i < indices_length; i++) {
      auto i_vec = dbTensor.slice(0, indices[i], indices[i] + 1).contiguous().data_ptr<float>();
      float *center = &centers[belongs_to[i] * vecDim];
      for (int64_t k = 0; k < vecDim; k++) {
        center[k] += i_vec[k];
      }
    }
    for (int64_t i = 0; i < branching; i++) {
      auto cnt = count[i];
      float div_factor = 1.0 / cnt;
      for (int64_t k = 0; k < vecDim; k++) {
        centers[i * vecDim + k] *= div_factor;
      }
    }

    // reassign points to clusters;
    for (int64_t i = 0; i < indices_length; i++) {
      auto i_vec = dbTensor.slice(0, indices[i], indices[i] + 1).contiguous().data_ptr<float>();
      float sq_dist;
      if (faissMetric == faiss::METRIC_L2) {
        sq_dist = faiss::fvec_L2sqr(i_vec, &centers[0], vecDim);
      }
      if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
        sq_dist = -faiss::fvec_inner_product(i_vec, &centers[0], vecDim);
      }
      int64_t new_centroid = 0;
      for (int64_t j = 0; j < branching; j++) {
        float new_dist;
        if (faissMetric == faiss::METRIC_L2) {
          new_dist = faiss::fvec_L2sqr(i_vec, &centers[j * vecDim], vecDim);
        }
        if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
          new_dist = -faiss::fvec_inner_product(i_vec, &centers[j * vecDim], vecDim);
        }
        if (sq_dist > new_dist) {
          sq_dist = new_dist;
          new_centroid = j;
        }
      }
      if (sq_dist > radiuses[new_centroid]) {
        radiuses[new_centroid] = sq_dist;
      }
      if (new_centroid != belongs_to[i]) {
        count[belongs_to[i]]--;
        count[new_centroid]++;
        belongs_to[i] = new_centroid;
        converged = false;
      }
    }

    // if converged to empty, make it unempty
    for (int64_t i = 0; i < branching; i++) {
      if (count[i] == 0) {
        auto j = (i + 1) % branching;
        while (count[j] <= 1) {
          j = (j + 1) % branching;
        }
        for (int64_t k = 0; k < indices_length; k++) {
          if (belongs_to[k] == j) {
            belongs_to[k] = i;
            count[j]--;
            count[i]++;
            break;
          }
        }
        converged = false;
      }
    }

    // compute kmeans cluster for resulting clusters
    node->childs.resize(branching);
    int start = 0;
    int end = 0;
    for (int64_t c = 0; c < branching; c++) {
      int s = count[c];
      float variance = 0;
      for (int64_t i = 0; i < indices_length; i++) {
        auto i_vec = dbTensor.slice(0, indices[i], indices[i] + 1).contiguous().data_ptr<float>();
        if (belongs_to[i] == c) {
          if (faissMetric == faiss::METRIC_L2) {
            variance += faiss::fvec_L2sqr(&centers[c * vecDim], i_vec, vecDim);
          }
          if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
            variance -= faiss::fvec_inner_product(&centers[c * vecDim], i_vec, vecDim);
          }
          std::swap(indices[i], indices[end]);
          std::swap(belongs_to[i], belongs_to[end]);
          end++;
        }
      }
      variance /= s;

      node->childs[c] = new Node();
      node->childs[c]->radius = radiuses[c];
      node->childs[c]->pivot = &centers[c * vecDim];
      computeClustering(node->childs[c], indices + start, end - start, branching);
      start = end;
    }
  }
}

int CANDY::KmeansTree::knnSearch(torch::Tensor &q, int64_t *idx, float *distances, int64_t aknn) {
  int count = 0;

  for (int64_t i = 0; i < q.size(0); i++) {
    CANDY::FLANN::ResultSet resultSet = CANDY::FLANN::ResultSet(aknn);

    auto query_data = q.slice(0, i, i + 1).contiguous().data_ptr<float>();

    getNeighbors(resultSet, query_data, checks);
    int64_t n = std::min(resultSet.size(), (size_t) aknn);
    resultSet.copy(idx, distances, i, n);
    //resultSet.copy(idx,distances,n);
    count += n;
  }
  return count;
}

void CANDY::KmeansTree::getNeighbors(FLANN::ResultSet &result, float *vec, int maxCheck) {
  CANDY::FLANN::Heap<BranchSt> *heap = new CANDY::FLANN::Heap<BranchSt>(ntotal);
  int check = 0;
  findNN(root, result, vec, check, checks, heap);

  BranchSt branch;
  while (heap->popMin(branch) && (check < maxCheck || !result.isFull())) {
    NodePtr node = branch.node;
    findNN(node, result, vec, check, checks, heap);
  }
}

void CANDY::KmeansTree::findNN(NodePtr node,
                               FLANN::ResultSet &result,
                               float *vec,
                               int &check,
                               int maxCheck,
                               FLANN::Heap<BranchSt> *heap) {
  // ignore if too far away
  float dist;
  if (faissMetric == faiss::METRIC_L2) {
    dist = faiss::fvec_L2sqr(vec, node->pivot, vecDim);
  }
  if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
    dist = -faiss::fvec_inner_product(vec, node->pivot, vecDim);
  }
  auto rad = node->radius;
  auto worst = result.worstDist();
  auto val1 = dist - rad - worst;
  auto val2 = val1 * val1 - 4 * rad * worst;
  if (val1 > 0 && val2 > 0) {
    return;
  }

  if (node->childs.empty()) {
    if (check > maxCheck) {
      if (result.isFull()) {
        return;
      }
    }
    for (int64_t i = 0; i < node->size; i++) {
      auto point_info = node->points[i];
      auto index = point_info.index;
      float cur_dist;
      if (faissMetric == faiss::METRIC_L2) {
        cur_dist = faiss::fvec_L2sqr(point_info.point.contiguous().data_ptr<float>(), vec, vecDim);
      }
      if (faissMetric == faiss::METRIC_INNER_PRODUCT) {
        cur_dist = -faiss::fvec_inner_product(point_info.point.contiguous().data_ptr<float>(), vec, vecDim);
      }
      //printf("adding %ld %f\n", index, cur_dist);
      result.add(cur_dist, index);
      ++check;
    }
  } else {
    int64_t closest_center = explore(node, vec, heap);
    findNN(node->childs[closest_center], result, vec, check, maxCheck, heap);
  }
}

int64_t CANDY::KmeansTree::explore(NodePtr node, float *q, CANDY::FLANN::Heap<BranchSt> *heap) {
  std::vector<float> distances(branching);
  int64_t best_index = 0;
  if (faissMetric == faiss::METRIC_L2) {
    distances[best_index] = -faiss::fvec_inner_product(node->childs[best_index]->pivot, q, vecDim);
  } else {
    distances[best_index] = faiss::fvec_L2sqr(node->childs[best_index]->pivot, q, vecDim);
  }

  for (int64_t i = 0; i < branching; i++) {
    if (faissMetric == faiss::METRIC_L2) {
      distances[i] = -faiss::fvec_inner_product(node->childs[i]->pivot, q, vecDim);
    } else {
      distances[i] = faiss::fvec_L2sqr(node->childs[i]->pivot, q, vecDim);
    }
    if (distances[i] < distances[best_index]) {
      best_index = i;
    }
  }

  for (int64_t i = 0; i < branching; i++) {
    if (i != best_index) {
      distances[i] -= cb_index * node->childs[i]->variance;
      heap->insert(BranchSt(node->childs[i], distances[i]));
    }
  }
  return best_index;
}
