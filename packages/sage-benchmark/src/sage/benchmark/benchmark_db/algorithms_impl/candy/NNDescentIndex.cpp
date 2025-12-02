/*! \file NNDescentIndex.cpp*/
//
// Created by honeta on 21/02/24.
//

#include <NNDescentIndex.h>

namespace CANDY {
void NNDescentIndex::nnDescent() {
  std::mt19937 rng(time(NULL));
  while (true) {
    parallelFor(graph.size(), [&](size_t i) {
      std::unordered_set<size_t>().swap(graph[i].nnNew);
      std::unordered_set<size_t>().swap(graph[i].nnOld);
      std::unordered_set<size_t>().swap(graph[i].rnnNew);
      std::unordered_set<size_t>().swap(graph[i].rnnOld);
    });

    parallelFor(graph.size(), [&](size_t i) {
      std::vector<std::pair<size_t, size_t>> nnNewWithIdx;
      for (size_t j = 0; j < graph[i].pool.size(); ++j) {
        auto &neighbor = graph[i].pool[j];
        if (neighbor.flag) {
          nnNewWithIdx.push_back({neighbor.id, j});
        } else {
          graph[i].nnOld.insert(neighbor.id);
          std::lock_guard<std::mutex> lockGuard(graph[neighbor.id].rnnOldLock);
          graph[neighbor.id].rnnOld.insert(i);
        }
      }
      std::vector<size_t> sampledIdx;
      randomSample(rng, sampledIdx, nnNewWithIdx.size(), rho * graphK);
      for (auto idx : sampledIdx) {
        graph[i].nnNew.insert(nnNewWithIdx[idx].first);
        graph[i].pool[nnNewWithIdx[idx].second].flag = false;
        std::lock_guard<std::mutex> lockGuard(
            graph[nnNewWithIdx[idx].first].rnnNewLock);
        graph[nnNewWithIdx[idx].first].rnnNew.insert(i);
      }
    });

    std::atomic<size_t> counter(0);
    parallelFor(graph.size(), [&](size_t i) {
      std::vector<size_t> sampledIdx;

      randomSample(rng, sampledIdx, graph[i].rnnOld.size(), rho * graphK);
      size_t insertCount = 0, iterateOffset = 0;
      for (auto it = graph[i].rnnOld.begin();
           it != graph[i].rnnOld.end(), insertCount < sampledIdx.size();
           ++it, ++iterateOffset)
        if (iterateOffset == sampledIdx[insertCount++])
          graph[i].nnOld.insert(*it);

      randomSample(rng, sampledIdx, graph[i].rnnNew.size(), rho * graphK);
      insertCount = iterateOffset = 0;
      for (auto it = graph[i].rnnNew.begin();
           it != graph[i].rnnNew.end(), insertCount < sampledIdx.size();
           ++it, ++iterateOffset)
        if (iterateOffset == sampledIdx[insertCount++])
          graph[i].nnNew.insert(*it);

      for (auto u1 : graph[i].nnNew) {
        for (auto u2 : graph[i].nnNew)
          if (u1 < u2) {
            auto dist = calcDist(tensor[u1], tensor[u2]);
            counter.fetch_add(updateNN(u1, u2, dist),
                              std::memory_order_relaxed);
            counter.fetch_add(updateNN(u2, u1, dist),
                              std::memory_order_relaxed);
          }
        for (auto u2 : graph[i].nnOld)
          if (u1 < u2) {
            auto dist = calcDist(tensor[u1], tensor[u2]);
            counter.fetch_add(updateNN(u1, u2, dist),
                              std::memory_order_relaxed);
            counter.fetch_add(updateNN(u2, u1, dist),
                              std::memory_order_relaxed);
          }
      }
    });
    if (counter < delta * graph.size() * graphK) return;
  }
}

void NNDescentIndex::randomSample(std::mt19937 &rng, std::vector<size_t> &vec,
                                  size_t n, size_t sampledCount) {
  if (sampledCount >= n) {
    vec.resize(n);
    for (size_t i = 0; i < n; ++i) vec[i] = i;
    return;
  }
  vec.resize(sampledCount);
  for (size_t i = 0; i < sampledCount; ++i) {
    vec[i] = rng() % (n - sampledCount);
  }
  std::sort(vec.begin(), vec.end());
  for (size_t i = 1; i < sampledCount; ++i) {
    if (vec[i] <= vec[i - 1]) {
      vec[i] = vec[i - 1] + 1;
    }
  }
  size_t off = rng() % n;
  for (size_t i = 0; i < sampledCount; ++i) {
    vec[i] = (vec[i] + off) % n;
  }
}

bool NNDescentIndex::updateNN(size_t i, size_t j, double dist) {
  std::lock_guard<std::mutex> lockGuard(graph[i].poolLock);
  if (graph[i].pool.size() < graphK) {
    graph[i].neighborIdxSet.insert(j);

    graph[i].pool.emplace_back(j, dist, true);
    std::push_heap(graph[i].pool.begin(), graph[i].pool.end());
    return true;
  } else if (dist < graph[i].pool.front().distance &&
             !graph[i].neighborIdxSet.count(j)) {
    graph[i].neighborIdxSet.erase(graph[i].pool.front().id);
    graph[i].neighborIdxSet.insert(j);

    std::pop_heap(graph[i].pool.begin(), graph[i].pool.end());
    graph[i].pool.back() = {j, dist, true};
    std::push_heap(graph[i].pool.begin(), graph[i].pool.end());
    return true;
  }
  return false;
}

double NNDescentIndex::calcDist(const torch::Tensor &ta,
                                const torch::Tensor &tb) {
  double ans = 0;
  if (faissMetric == faiss::METRIC_L2) {
    // Calculate the squared L2 distance as ||v1 - v2||^2
    auto diff = ta-tb;
    auto l2_sqr = torch::sum(diff * diff);
    // Convert the result back to float and return
    ans = l2_sqr.item<float>();
  } else {
    //for (size_t i = 0; i < vecDim; ++i) ans -= taPtr[i] * tbPtr[i];
    // Calculate the inner (dot) product
    auto inner_product = torch::matmul(ta, tb.t());
    ans = -inner_product.item<float>();
    // Convert the result back to float and return
  }
  return ans;
}

torch::Tensor NNDescentIndex::searchOnce(torch::Tensor q, int64_t k) {
  auto neighbors = searchOnceInner(q, k);
  auto ans = torch::zeros({int64_t(neighbors.size()), vecDim});
  for (size_t i = 0; i < neighbors.size(); ++i)
    ans.slice(0, i, i + 1) = tensor[neighbors[i].second];
  return ans;
}

std::vector<std::pair<double, size_t>> NNDescentIndex::searchOnceInner(
    torch::Tensor q, int64_t k) {
  if (graph.empty()) return std::vector<std::pair<double, size_t>>();
  std::mt19937 rng(time(NULL));
  size_t startId = rng() % graph.size();
  std::vector<std::pair<double, size_t>> neighbors;
  neighbors.reserve(k);
  std::unordered_map<size_t, bool> neighborIdxWithVisitFlag;
  size_t deletedCountInNeighbors = 0;
  neighbors.emplace_back(calcDist(tensor[startId], q), startId);
  neighborIdxWithVisitFlag.insert({startId, false});

  bool exit;
  do {
    exit = true;
    auto curNeighbors = neighbors;
    for (auto item : curNeighbors)
      if (!neighborIdxWithVisitFlag[item.second]) {
        neighborIdxWithVisitFlag[item.second] = true;
        exit = false;
        for (auto neighbor : graph[item.second].pool)
          if (!neighborIdxWithVisitFlag.count(neighbor.id)) {
            auto dist = calcDist(tensor[neighbor.id], q);
            if (neighbors.size() < k + deletedCountInNeighbors) {
              neighborIdxWithVisitFlag.insert({neighbor.id, false});
              if (deletedIdxSet.count(neighbor.id)) ++deletedCountInNeighbors;

              neighbors.emplace_back(dist, neighbor.id);
              std::push_heap(neighbors.begin(), neighbors.end());
            } else if (calcDist(tensor[neighbor.id], q) <
                       neighbors.front().first) {
              neighborIdxWithVisitFlag.erase(neighbors.front().second);
              neighborIdxWithVisitFlag.insert(
                  std::make_pair(neighbor.id, false));
              if (deletedIdxSet.count(neighbors.front().second))
                --deletedCountInNeighbors;
              if (deletedIdxSet.count(neighbor.id)) ++deletedCountInNeighbors;

              std::pop_heap(neighbors.begin(), neighbors.end());
              neighbors.back() = std::make_pair(dist, neighbor.id);
              std::push_heap(neighbors.begin(), neighbors.end());
            }
          }
      }
  } while (!exit);

  std::vector<std::pair<double, size_t>> finalNeighbors;
  finalNeighbors.reserve(neighbors.size() - deletedCountInNeighbors);
  for (auto &item : neighbors)
    if (!deletedIdxSet.count(item.second)) finalNeighbors.push_back(item);
  return finalNeighbors;
}

bool NNDescentIndex::insertOnce(vector<std::pair<double, size_t>> &neighbors,
                                torch::Tensor t) {
  tensor.push_back(t);
  graph.emplace_back();
  graph.back().pool.resize(neighbors.size());
  parallelFor(neighbors.size(), [&](size_t i) {
    graph.back().pool[i] =
        Neighbor(neighbors[i].second, neighbors[i].first, true);
    updateNN(neighbors[i].second, graph.size() - 1, neighbors[i].first);
  });
  return true;
}

bool NNDescentIndex::deleteOnce(torch::Tensor t, int64_t k) {
  auto neighbors = searchOnceInner(t, k);
  for (auto item : neighbors) deletedIdxSet.insert(item.second);
  return true;
}

void NNDescentIndex::parallelFor(size_t idxSize,
                                 std::function<void(size_t)> action) {
  std::vector<std::shared_ptr<std::thread>> threads(parallelWorkers);
  size_t itemPerThread = (idxSize + parallelWorkers - 1) / parallelWorkers;
  for (size_t id = 0; id < parallelWorkers; ++id)
    threads[id] = std::make_shared<std::thread>([=]() {
      size_t threadBegin = id * itemPerThread,
             threadEnd = std::min(idxSize, (id + 1) * itemPerThread);
      for (size_t i = threadBegin; i < threadEnd; ++i) action(i);
    });
  for (auto thread : threads) thread->join();
}

bool NNDescentIndex::loadInitialTensor(torch::Tensor &t) {
  if (frozenLevel == 0) return false;
  tensor.reserve(tensor.size() + t.size(0));
  for (size_t i = 0; i < t.size(0); ++i) tensor.push_back(t.slice(0, i, i + 1));
  return true;
}

void NNDescentIndex::reset() {
  tensor.clear();
  graph.clear();
  deletedIdxSet.clear();
}

bool NNDescentIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  std::string metricType = cfg->tryString("metricType", "L2", true);
  faissMetric = faiss::METRIC_L2;
  if (metricType == "dot" || metricType == "IP" || metricType == "cossim") {
    faissMetric = faiss::METRIC_INNER_PRODUCT;
  }
  graphK = cfg->tryI64("graphK", 20, true);
  vecDim = cfg->tryI64("vecDim", 768, true);
  rho = cfg->tryDouble("rho", 1.0, true);
  delta = cfg->tryDouble("delta", 0.01, true);
  parallelWorkers = cfg->tryI64("parallelWorkers", 1, true);
  if (parallelWorkers <= 0)
    parallelWorkers = std::thread::hardware_concurrency();
  return true;
}

bool NNDescentIndex::insertTensor(torch::Tensor &t) {
  if (frozenLevel == 0) return false;
  graph.reserve(graph.size() + t.size(0));
  tensor.reserve(tensor.size() + t.size(0));
  for (size_t i = 0; i < t.size(0); ++i) {
    auto neighbors = searchOnceInner(t.slice(0, i, i + 1), graphK);
    insertOnce(neighbors, t.slice(0, i, i + 1));
  }
  return true;
}

bool NNDescentIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  if (frozenLevel == 0) return false;
  for (size_t i = 0; i < t.size(0); ++i) deleteOnce(t.slice(0, i, i + 1), k);
  return true;
}

bool NNDescentIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  if (!deleteTensor(t)) return false;
  return insertTensor(w);
}

std::vector<torch::Tensor> NNDescentIndex::getTensorByIndex(
    std::vector<faiss::idx_t> &idx, int64_t k) {
  std::vector<torch::Tensor> ret;
  size_t offset = 0;
  for (size_t i = 0; i < tensor.size(); ++i)
    if (!deletedIdxSet.count(i)) {
      if (offset == idx[ret.size()]) ret.push_back(tensor[i]);
      ++offset;
    }
  return ret;
}

torch::Tensor NNDescentIndex::rawData() {
  if (tensor.size() - deletedIdxSet.size() == 0) {
    return torch::Tensor();
  }
  auto ret =
      torch::zeros({int64_t(tensor.size() - deletedIdxSet.size()), vecDim});
  size_t offset = 0;
  for (size_t i = 0; i < tensor.size(); ++i)
    if (!deletedIdxSet.count(i)) {
      ret.slice(0, offset, offset + 1) = tensor[i];
      ++offset;
    }
  return ret;
}

std::vector<torch::Tensor> NNDescentIndex::searchTensor(torch::Tensor &q,
                                                        int64_t k) {
  std::vector<torch::Tensor> ans(q.size(0));
  parallelFor(ans.size(),
              [&](size_t i) { ans[i] = searchOnce(q.slice(0, i, i + 1), k); });
  return ans;
}

bool NNDescentIndex::startHPC() { return true; }

bool NNDescentIndex::endHPC() { return true; }

bool NNDescentIndex::setFrozenLevel(int64_t frozenLv) {
  frozenLevel = frozenLv;
  return true;
}

bool NNDescentIndex::offlineBuild(torch::Tensor &t) {
  if (!loadInitialTensor(t)) return false;
  std::mt19937 rng(time(NULL));
  graph.resize(tensor.size());
  for (size_t i = 0; i < tensor.size(); ++i) {
    std::vector<size_t> sampledIdx;
    randomSample(rng, sampledIdx, tensor.size() - 1, graphK);
    graph[i].pool.resize(sampledIdx.size());
    for (size_t j = 0; j < sampledIdx.size(); ++j) {
      auto idx = sampledIdx[j];
      idx += (idx >= i);
      graph[i].pool[j] = Neighbor(idx, calcDist(tensor[idx], tensor[i]), true);
      graph[i].neighborIdxSet.insert(idx);
    }
    std::make_heap(graph[i].pool.begin(), graph[i].pool.end());
  }
  nnDescent();
  return true;
}
}  // namespace CANDY
