//
// Created by Isshin on 2024/1/16.
//
#include <HNSWNaiveIndex.h>

bool CANDY::HNSWNaiveIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  assert(cfg);
  is_NSW = cfg->tryI64("is_NSW", 0, true);
  vecDim = cfg->tryI64("vecDim", 768, true);
  M_ = cfg->tryI64("maxConnection", 32, true);
  std::string metricType = cfg->tryString("metricType", "L2", true);
  faissMetric = faiss::METRIC_L2;
  if (metricType == "dot" || metricType == "IP" || metricType == "cossim") {
      faissMetric = faiss::METRIC_INNER_PRODUCT;
  }
  hnsw = HNSW(vecDim, M_);


  opt_mode_ = cfg->tryI64("opt_mode", 0, true);
  hnsw.set_mode(opt_mode_, faissMetric);

    if(opt_mode_ == OPT_DCO){
        adSampling_step = cfg->tryI64("samplingStep", 64, true);
        adSampling_epsilon0 = cfg->tryDouble("ads_epsilon", 1.0,true);
        printf("adSampling_step = %ld\n", adSampling_step);
    }

  storage = new CANDY::FlatIndex();
  storage->setConfig(cfg);
  return true;
}

bool CANDY::HNSWNaiveIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  // TODO: impl
  return false;
}

bool CANDY::HNSWNaiveIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  // TODO: impl
  return false;
}
bool CANDY::HNSWNaiveIndex::insertTensor(torch::Tensor &t) {
  auto n = t.size(0);
  hnsw.levels_ = std::vector<int>(n, -1);
  int max_level = hnsw.prepare_level_tab(t, false, is_NSW);

  if (is_NSW) {
    // only need to insert all vectors at level 0
    INTELLI_INFO("START INSERTION AS NSW");
    CANDY::VisitedTable vt;
    auto qdis = new CANDY::DistanceQueryer(vecDim);
    qdis->set_mode(opt_mode_, faissMetric);
    if (qdis->opt_mode_ == OPT_LVQ) {
      qdis->mean_ = &hnsw.mean_;
    }
    for (size_t i = 0; i < n; i++) {
      auto id = newTensor(t.slice(0, i, i + 1));
      auto level = 0;
      auto new_in_vertex = std::make_shared<CANDY::HNSWVertex>(
          CANDY::HNSWVertex(id, level, hnsw.cum_nb_neighbors(level + 1)));
      qdis->set_query(*id);
      hnsw.add_without_lock(*qdis, level, new_in_vertex, vt);
    }
  } else {
    // need to add the vector from higher to lower level
    // making buckets for each level
    std::vector<std::vector<INTELLI::TensorPtr>> orders(
        max_level + 1, std::vector<INTELLI::TensorPtr>(0));
    for (int64_t i = 0; i < n; i++) {
      auto id = newTensor(t.slice(0, i, i + 1));
      auto assigned_level = hnsw.levels_[i] - 1;
      orders[assigned_level].push_back(id);
      // INTELLI_INFO("LEVEL: "+std::to_string(assigned_level));
    }
      auto qdis = new CANDY::DistanceQueryer(vecDim);

      qdis->set_mode(opt_mode_, faissMetric);
      if (qdis->opt_mode_ == OPT_LVQ) {
          qdis->mean_ = &hnsw.mean_;
      }
      if (qdis->opt_mode_ == OPT_DCO){
          qdis->ads->set_transformed(&hnsw.transformMatrix);
          qdis->ads->set_step(adSampling_step,adSampling_epsilon0);
      }
      int j=0;
    for (int level = orders.size() - 1; level >= 0; level--) {
      CANDY::VisitedTable vt;


      for (size_t i = 0; i < orders[level].size(); i++) {
        auto id = orders[level][i];
        auto new_in_vertex = std::make_shared<CANDY::HNSWVertex>(
            CANDY::HNSWVertex(id, level, hnsw.cum_nb_neighbors(level + 1)));
        new_in_vertex->vid = ntotal+j;
        qdis->set_query(*id);
        if(qdis->opt_mode_ == OPT_LVQ && is_local_lvq) {
            new_in_vertex->code_final_ = qdis->compute_code(id);
        }
        if(qdis->opt_mode_ == OPT_DCO){
            auto transformed = qdis->compute_transformed(id);
            new_in_vertex->transformed = newTensor(transformed);
        }
        hnsw.add_without_lock(*qdis, level, new_in_vertex, vt);
        j++;
      }
    }
  }
  ntotal += n;
  return true;
}
std::vector<torch::Tensor> CANDY::HNSWNaiveIndex::searchTensor(torch::Tensor &q,
                                                               int64_t k) {
  CANDY::DistanceQueryer disq(vecDim);
  disq.set_mode(opt_mode_, faissMetric);
  disq.set_search(true);
  if (disq.opt_mode_ == OPT_LVQ) {
    disq.mean_ = &hnsw.mean_;
  }
    if(disq.opt_mode_ == OPT_DCO){
        disq.ads->set_transformed(&hnsw.transformMatrix);
        disq.ads->set_step(adSampling_step,adSampling_epsilon0);
    }
  int64_t query_size = q.size(0);
  std::vector<torch::Tensor> ru(query_size);
  CANDY::VisitedTable vt;
  for (int64_t i = 0; i < query_size; i++) {
    auto query = q.slice(0, i, i + 1);
    if(disq.opt_mode_ == OPT_DCO){
        disq.set_query(query);

        auto transformed = disq.ads->transform(query);
        disq.transformed = transformed;
    } else {
        disq.set_query(query);
    }
    ru[i] = torch::zeros({k, vecDim});
    auto D = std::vector<float>(k);
    auto I = std::vector<CANDY::VertexPtr>(k);

    hnsw.search(disq, k, I, D.data(), vt);
    for (int64_t j = 0; j < k; j++) {
      ru[i].slice(0, j, j + 1) = *(I[j]->id);
    }
  }
  return ru;
}

std::vector<faiss::idx_t> CANDY::HNSWNaiveIndex::searchIndex(torch::Tensor q, int64_t k) {
    CANDY::DistanceQueryer disq(vecDim);
    disq.set_mode(opt_mode_, faissMetric);
    disq.set_search(true);
    if (disq.opt_mode_ == OPT_LVQ) {
        disq.mean_ = &hnsw.mean_;
    }
    if(disq.opt_mode_ == OPT_DCO){
        disq.ads->set_transformed(&hnsw.transformMatrix);
        disq.ads->set_step(adSampling_step,adSampling_epsilon0);
    }
    int64_t query_size = q.size(0);
    std::vector<faiss::idx_t> ru(query_size*k);
    CANDY::VisitedTable vt;
    for (int64_t i = 0; i < query_size; i++) {
        auto query = q.slice(0, i, i + 1);
        if(disq.opt_mode_ == OPT_DCO){
            disq.set_query(query);

            auto transformed = disq.ads->transform(query);
            disq.transformed = transformed;
        } else {
            disq.set_query(query);
        }
        auto D = std::vector<float>(k);
        auto I = std::vector<CANDY::VertexPtr>(k);

        hnsw.search(disq, k, I, D.data(), vt);
        for (int64_t j = 0; j < k; j++) {
            ru[i*k+j]= I[j]->vid;
        }
    }
    return ru;
}
