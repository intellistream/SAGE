/*! \file DPGIndex.cpp*/
//
// Created by honeta on 04/04/24.
//

#include <DPGIndex.h>

namespace CANDY {
void DPGIndex::nnDescent() {
  std::mt19937 rng(time(NULL));
  while (true) {
    parallelFor(graphLayer0.size(), [&](size_t i) {
      std::unordered_set<size_t>().swap(graphLayer0[i].nnNew);
      std::unordered_set<size_t>().swap(graphLayer0[i].nnOld);
      std::unordered_set<size_t>().swap(graphLayer0[i].rnnNew);
      std::unordered_set<size_t>().swap(graphLayer0[i].rnnOld);
    });

    parallelFor(graphLayer0.size(), [&](size_t i) {
      std::vector<std::pair<size_t, size_t>> nnNewWithIdx;
      for (size_t j = 0; j < graphLayer0[i].pool.size(); ++j) {
        auto &neighbor = graphLayer0[i].pool[j];
        if (neighbor.flag) {
          nnNewWithIdx.push_back({neighbor.id, j});
        } else {
          graphLayer0[i].nnOld.insert(neighbor.id);
          std::lock_guard<std::mutex> lockGuard(
              graphLayer0[neighbor.id].rnnOldLock);
          graphLayer0[neighbor.id].rnnOld.insert(i);
        }
      }
      std::vector<size_t> sampledIdx;
      randomSample(rng, sampledIdx, nnNewWithIdx.size(), rho * graphK);
      for (auto idx : sampledIdx) {
        graphLayer0[i].nnNew.insert(nnNewWithIdx[idx].first);
        graphLayer0[i].pool[nnNewWithIdx[idx].second].flag = false;
        std::lock_guard<std::mutex> lockGuard(
            graphLayer0[nnNewWithIdx[idx].first].rnnNewLock);
        graphLayer0[nnNewWithIdx[idx].first].rnnNew.insert(i);
      }
    });

    std::atomic<size_t> counter(0);
    parallelFor(graphLayer0.size(), [&](size_t i) {
      std::vector<size_t> sampledIdx;

      randomSample(rng, sampledIdx, graphLayer0[i].rnnOld.size(), rho * graphK);
      size_t insertCount = 0, iterateOffset = 0;
      for (auto it = graphLayer0[i].rnnOld.begin();
           it != graphLayer0[i].rnnOld.end(), insertCount < sampledIdx.size();
           ++it, ++iterateOffset)
        if (iterateOffset == sampledIdx[insertCount++])
          graphLayer0[i].nnOld.insert(*it);

      randomSample(rng, sampledIdx, graphLayer0[i].rnnNew.size(), rho * graphK);
      insertCount = iterateOffset = 0;
      for (auto it = graphLayer0[i].rnnNew.begin();
           it != graphLayer0[i].rnnNew.end(), insertCount < sampledIdx.size();
           ++it, ++iterateOffset)
        if (iterateOffset == sampledIdx[insertCount++])
          graphLayer0[i].nnNew.insert(*it);

      for (auto u1 : graphLayer0[i].nnNew) {
        for (auto u2 : graphLayer0[i].nnNew)
          if (u1 < u2) {
            auto dist = calcDist(tensor[u1], tensor[u2]);
            auto neighborUpdated = updateLayer0Neighbor(u1, u2, dist),
                 reverseNeighborUpdated = updateLayer0Neighbor(u2, u1, dist);
            counter.fetch_add(updateLayer0Neighbor(u1, u2, dist),
                              std::memory_order_relaxed);
            counter.fetch_add(updateLayer0Neighbor(u2, u1, dist),
                              std::memory_order_relaxed);
          }
        for (auto u2 : graphLayer0[i].nnOld)
          if (u1 < u2) {
            auto dist = calcDist(tensor[u1], tensor[u2]);
            counter.fetch_add(updateLayer0Neighbor(u1, u2, dist),
                              std::memory_order_relaxed);
            counter.fetch_add(updateLayer0Neighbor(u2, u1, dist),
                              std::memory_order_relaxed);
          }
      }
    });
    if (counter < delta * graphLayer0.size() * graphK) return;
  }
}

void DPGIndex::randomSample(std::mt19937 &rng, std::vector<size_t> &vec,
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

bool DPGIndex::updateLayer0Neighbor(size_t i, size_t j, double dist) {
  std::lock_guard<std::mutex> lockGuard(graphLayer0[i].poolLock);
  if (graphLayer0[i].pool.size() < graphK) {
    graphLayer0[i].neighborIdxSet.insert(j);
    addLayer1Neighbor(i, j);

    graphLayer0[i].pool.emplace_back(j, dist, true);
    std::push_heap(graphLayer0[i].pool.begin(), graphLayer0[i].pool.end());
    return true;
  } else if (dist < graphLayer0[i].pool.front().distance &&
             !graphLayer0[i].neighborIdxSet.count(j)) {
    graphLayer0[i].neighborIdxSet.erase(graphLayer0[i].pool.front().id);
    graphLayer0[i].neighborIdxSet.insert(j);
    removeLayer1Neighbor(i, graphLayer0[i].pool.front().id);
    addLayer1Neighbor(i, j);

    std::pop_heap(graphLayer0[i].pool.begin(), graphLayer0[i].pool.end());
    graphLayer0[i].pool.back() = {j, dist, true};
    std::push_heap(graphLayer0[i].pool.begin(), graphLayer0[i].pool.end());
    return true;
  }
  return false;
}

void DPGIndex::addLayer1Neighbor(size_t i, size_t j) {
  std::lock_guard<std::mutex> lockGuard(graphLayer1[i].neighborLock);
  if (graphLayer1[i].neighborIdxSet.size() < graphK >> 1) {
    graphLayer1[i].neighborIdxSet.insert(j);
    std::lock_guard<std::mutex> lockGuard(graphLayer1[j].reverseNeighborLock);
    graphLayer1[j].reverseNeighborIdxSet.insert(i);
  }
}

void DPGIndex::removeLayer1Neighbor(size_t i, size_t j) {
  {
    std::lock_guard<std::mutex> lockGuard(graphLayer1[i].neighborLock);
    graphLayer1[i].neighborIdxSet.erase(j);
  }
  {
    std::lock_guard<std::mutex> lockGuard(graphLayer1[j].reverseNeighborLock);
    graphLayer1[j].reverseNeighborIdxSet.erase(i);
  }
}

double DPGIndex::calcDist(const torch::Tensor &ta, const torch::Tensor &tb) {

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

torch::Tensor DPGIndex::searchOnce(torch::Tensor q, int64_t k) {
  auto neighbors = searchOnceInner(q, k);
  auto ans = torch::zeros({int64_t(neighbors.size()), vecDim});
  for (size_t i = 0; i < neighbors.size(); ++i)
    ans.slice(0, i, i + 1) = tensor[neighbors[i].second];
  return ans;
}

std::vector<faiss::idx_t> DPGIndex::searchOnceIndex(torch::Tensor q, int64_t k) {
    auto neighbors = searchOnceInner(q, k);
    auto ans = std::vector<faiss::idx_t>(k);
    for (size_t i = 0; i < neighbors.size(); ++i)
        ans[i] = neighbors[i].second;
    return ans;
}

std::vector<std::pair<double, size_t>> DPGIndex::searchOnceInner(
    torch::Tensor q, int64_t k) {
  if (graphLayer1.empty()) return std::vector<std::pair<double, size_t>>();
  std::mt19937 rng(time(NULL));
  size_t startId = rng() % graphLayer1.size();
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
        for (auto &neighborIdxSet :
             {graphLayer1[item.second].neighborIdxSet,
              graphLayer1[item.second].reverseNeighborIdxSet})
          for (auto id : neighborIdxSet)
            if (!neighborIdxWithVisitFlag.count(id)) {
              auto dist = calcDist(tensor[id], q);
              if (neighbors.size() < k + deletedCountInNeighbors) {
                neighborIdxWithVisitFlag.insert({id, false});
                if (deletedIdxSet.count(id)) ++deletedCountInNeighbors;

                neighbors.emplace_back(dist, id);
                std::push_heap(neighbors.begin(), neighbors.end());
              } else if (calcDist(tensor[id], q) < neighbors.front().first) {
                neighborIdxWithVisitFlag.erase(neighbors.front().second);
                neighborIdxWithVisitFlag.insert(std::make_pair(id, false));
                if (deletedIdxSet.count(neighbors.front().second))
                  --deletedCountInNeighbors;
                if (deletedIdxSet.count(id)) ++deletedCountInNeighbors;

                std::pop_heap(neighbors.begin(), neighbors.end());
                neighbors.back() = std::make_pair(dist, id);
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

bool DPGIndex::insertOnce(vector<std::pair<double, size_t>> &neighbors,
                          torch::Tensor t) {
  tensor.push_back(t);
  graphLayer0.emplace_back();
  graphLayer1.emplace_back();
  graphLayer0.back().pool.resize(neighbors.size());
  parallelFor(neighbors.size(), [&](size_t i) {
    graphLayer0.back().pool[i] =
        Neighbor(neighbors[i].second, neighbors[i].first, true);
    updateLayer0Neighbor(neighbors[i].second, graphLayer0.size() - 1,
                         neighbors[i].first);
  });
  buildLayer1(graphLayer0.size() - 1);
  return true;
}

bool DPGIndex::deleteOnce(torch::Tensor t, int64_t k) {
  auto neighbors = searchOnceInner(t, k);
  for (auto item : neighbors) deletedIdxSet.insert(item.second);
  return true;
}

void DPGIndex::parallelFor(size_t idxSize, std::function<void(size_t)> action) {
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

void DPGIndex::buildLayer1(size_t idx) {
  for (size_t i = 0; i < graphLayer0[idx].pool.size(); ++i)
    for (size_t j = 0; j < graphLayer0[idx].pool.size(); ++j)
      if (i != j &&
          calcDist(tensor[i], tensor[j]) < calcDist(tensor[idx], tensor[j])) {
        ++graphLayer0[idx].pool[j].counter;
      }
  std::vector<std::pair<size_t, size_t>> neighborsWithCounter;  // <counter, id>
  neighborsWithCounter.reserve(graphK >> 1);
  for (auto neighbor : graphLayer0[idx].pool) {
    if (neighborsWithCounter.size() < graphK >> 1) {
      neighborsWithCounter.emplace_back(neighbor.counter, neighbor.id);
      std::push_heap(neighborsWithCounter.begin(), neighborsWithCounter.end());
    } else if (neighbor.counter < neighborsWithCounter.front().first) {
      std::pop_heap(neighborsWithCounter.begin(), neighborsWithCounter.end());
      neighborsWithCounter.back() = {neighbor.counter, neighbor.id};
      std::push_heap(neighborsWithCounter.begin(), neighborsWithCounter.end());
    }
  }
  for (auto [_, id] : neighborsWithCounter) addLayer1Neighbor(idx, id);
}

bool DPGIndex::loadInitialTensor(torch::Tensor &t) {
  if (frozenLevel == 0) return false;
  tensor.reserve(tensor.size() + t.size(0));
  for (size_t i = 0; i < t.size(0); ++i) tensor.push_back(t.slice(0, i, i + 1));
  return true;
}

void DPGIndex::reset() {
  tensor.clear();
  graphLayer0.clear();
  graphLayer1.clear();
  deletedIdxSet.clear();
}

bool DPGIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
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

bool DPGIndex::insertTensor(torch::Tensor &t) {
  if (frozenLevel == 0) return false;
  graphLayer0.reserve(graphLayer0.size() + t.size(0));
  graphLayer1.reserve(graphLayer1.size() + t.size(0));
  tensor.reserve(tensor.size() + t.size(0));
  for (size_t i = 0; i < t.size(0); ++i) {
    auto neighbors = searchOnceInner(t.slice(0, i, i + 1), graphK);
    insertOnce(neighbors, t.slice(0, i, i + 1));
  }
  return true;
}

bool DPGIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  if (frozenLevel == 0) return false;
  for (size_t i = 0; i < t.size(0); ++i) deleteOnce(t.slice(0, i, i + 1), k);
  return true;
}

bool DPGIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  if (!deleteTensor(t)) return false;
  return insertTensor(w);
}

std::vector<torch::Tensor> DPGIndex::getTensorByIndex(
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

torch::Tensor DPGIndex::rawData() {
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


std::vector<faiss::idx_t> DPGIndex::searchIndex(torch::Tensor q, int64_t k){
    std::vector<faiss::idx_t> ans(k * q.size(0));
    parallelFor(ans.size(),
                [&](size_t i) {
        auto results = searchOnceIndex(q.slice(0,i,i+1),k);
        for(size_t j=0; j<k; j++){
                ans[i*k+j] = results[j]; };
                });
    return ans;
}

std::vector<torch::Tensor> DPGIndex::searchTensor(torch::Tensor &q, int64_t k) {
  std::vector<torch::Tensor> ans(q.size(0));
  parallelFor(ans.size(),
              [&](size_t i) { ans[i] = searchOnce(q.slice(0, i, i + 1), k); });
  return ans;
}

bool DPGIndex::startHPC() { return true; }

bool DPGIndex::endHPC() { return true; }

bool DPGIndex::setFrozenLevel(int64_t frozenLv) {
  frozenLevel = frozenLv;
  return true;
}

bool DPGIndex::offlineBuild(torch::Tensor &t) {
  if (!loadInitialTensor(t)) return false;
  std::mt19937 rng(time(NULL));
  graphLayer0.resize(tensor.size());
  graphLayer1.resize(tensor.size());
  for (size_t i = 0; i < tensor.size(); ++i) {
    std::vector<size_t> sampledIdx;
    randomSample(rng, sampledIdx, tensor.size() - 1, graphK);
    graphLayer0[i].pool.resize(sampledIdx.size());
    for (size_t j = 0; j < sampledIdx.size(); ++j) {
      auto idx = sampledIdx[j];
      idx += (idx >= i);
      graphLayer0[i].pool[j] =
          Neighbor(idx, calcDist(tensor[idx], tensor[i]), true);
      graphLayer0[i].neighborIdxSet.insert(idx);
    }
    std::make_heap(graphLayer0[i].pool.begin(), graphLayer0[i].pool.end());
  }
  nnDescent();
  parallelFor(graphLayer1.size(), [&](size_t i) { buildLayer1(i); });
  return true;
}
}  // namespace CANDY
