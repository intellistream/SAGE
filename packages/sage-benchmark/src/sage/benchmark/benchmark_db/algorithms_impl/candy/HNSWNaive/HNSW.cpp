//
// Created by Isshin on 2024/1/16.
//
#include <HNSWNaive/HNSW.h>
#include <Utils/UtilityFunctions.h>
#include <cmath>

void CANDY::HNSW::search(CANDY::DistanceQueryer &qdis, int k,
                         std::vector<CANDY::VertexPtr> &I, float *D,
                         CANDY::VisitedTable &vt) {
  if (entry_point_ == nullptr) {
    return;
  }
  qdis.set_search(true);
  qdis.set_rank(false);
  if (num_entries == 1) {
    auto nearest = entry_point_;
    float d_nearest;
    if(qdis.is_search && opt_mode_==OPT_LVQ){
        if(nearest->code_final_ == nullptr) {
            nearest->code_final_ = qdis.compute_code(nearest->id);
        }
        d_nearest = qdis(nearest->code_final_);
    } else {
        d_nearest = qdis(nearest->id);
    }



    for (int level = max_level_; level >= 1; level--) {
      nearest = greedy_update_nearest(*this,qdis, level, nearest, d_nearest);
    }

    int ef = efSearch > ((size_t)k) ? efSearch : k;
    qdis.set_rank(true);
    if (search_bounded_queue) {
      CANDY::HNSW::MinimaxHeap candidates(ef);
      candidates.push(nearest, d_nearest);
      search_from_candidates(*this, qdis, k, I, D, candidates, vt, 0, 0);
    } else {
    }
    vt.advance();
  } else {
  }
  return;
}

std::priority_queue<CANDY::HNSW::Node>
search_from_candidates_unbounded(CANDY::HNSW &hnsw, CANDY::HNSW::Node &node,
                                 CANDY::DistanceQueryer &qdis, size_t ef,
                                 CANDY::VisitedTable &vt) {
  std::priority_queue<CANDY::HNSW::Node> top_candidates;
  std::priority_queue<CANDY::HNSW::Node, std::vector<CANDY::HNSW::Node>,
                      std::greater<CANDY::HNSW::Node>>
      candidates;

  top_candidates.push(node);
  candidates.push(node);

  vt.set(node.second);
  while (!candidates.empty()) {
    float d0;
    INTELLI::TensorPtr v0;
    std::tie(d0, v0) = candidates.top();

    if (d0 > top_candidates.top().first) {
      break;
    }

    candidates.pop();

    size_t begin, end;
    hnsw.neighbor_range(0, &begin, &end);
    // auto nlist = hnsw.getNeighborsByPtr(v0);
    auto nlist = std::vector<INTELLI::TensorPtr>(0);

    for (auto it = nlist.begin() + begin;
         it != nlist.end() && it != nlist.begin() + end && begin < nlist.size();
         it++) {
      auto v1 = *it;
      if (v1 == nullptr) {
        break;
      }
      if (vt.get(v1)) {
        continue;
      }
      vt.set(v1);
      float d1 = qdis(v1);
//      float d1;
//      if(qdis.is_search && hnsw.opt_mode_ == OPT_LVQ){
//          if(v1->code_final_ == nullptr){
//              v1->code_final_ = qdis.compute_code(v1->id);
//          }
//          d=qdis(v1->code_final_);
//      } else {
//          d1 = qdis(v1->id);
//      }

      if (top_candidates.top().first > d1 || top_candidates.size() < ef) {
        candidates.emplace(d1, v1);
        top_candidates.emplace(d1, v1);
        if (top_candidates.size() > ef) {
          top_candidates.pop();
        }
      }
    }
  }
  return top_candidates;
}
int search_from_candidates(CANDY::HNSW &hnsw, CANDY::DistanceQueryer &qdis,
                           int k, std::vector<CANDY::VertexPtr> &I, float *D,
                           CANDY::HNSW::MinimaxHeap &candidates,
                           CANDY::VisitedTable &vt, int level, int nres_in) {
  int nres = nres_in;

  auto efSearch = hnsw.efSearch;
  // first push candidates into heap
  for (int i = 0; i < candidates.size(); i++) {
    auto v1 = candidates.ids[i];
    float d = candidates.dis[i];
    assert(v1 != nullptr);

    if (nres < k) {
      // std::cout<<"pushing  "<<*v1<<" with dist= "<<d<<" to heap"<<std::endl;
      faiss::heap_push<faiss::CMax<float, CANDY::VertexPtr>>(++nres, D,
                                                             I.data(), d, v1);
    } else if (d < D[0]) {
      // std::cout<<"pushing  "<<*v1<<" with dist= "<<d<<" to heap"<<std::endl;
      faiss::heap_replace_top<faiss::CMax<float, CANDY::VertexPtr>>(
          nres, D, I.data(), d, v1);
    }
    vt.set(v1);
  }
  size_t nstep = 0;
  // then push candidates' neighbors into heap
  int64_t visited_vertex=0;
  while (candidates.size() > 0) {
    float d0 = 0.0;
    auto v0 = candidates.pop_min(&d0);

    size_t begin, end;
    hnsw.neighbor_range(level, &begin, &end);
    // auto nlist = hnsw.getNeighborsByPtr(v0);
    auto nlist = v0->neighbors;

    for (auto it = nlist.begin() + begin;
         it != nlist.end() && it != nlist.begin() + end && begin < nlist.size();
         it++) {
      auto v1 = *it;
      if (v1 == nullptr) {
        break;
      }

      if (vt.get(v1)) {
        continue;
      }
      // std::cout<<"setting visited to "<<vt.visno<<" for "<<*v1<<std::endl;
      vt.set(v1);
      visited_vertex++;
      float d;

      if(qdis.is_search && hnsw.opt_mode_ == OPT_LVQ){
          if(v1->code_final_ == nullptr) {
              v1->code_final_ = qdis.compute_code(v1->id);
          }
          d=qdis(v1->code_final_);
      } else if(hnsw.opt_mode_==OPT_DCO){
          if(nres==k) {
              qdis.ads->set_threshold(D[0]);
          } else {
              qdis.ads->set_threshold(-1);
          }

          d=qdis(v1->transformed);
          //printf("%.2f ",d);
          if(d==-1){
              //nstep++;
              continue;
          }
      } else {
          d = qdis(v1->id);
      }
      if (nres < k) {
        // std::cout<<"pushing  "<<*v1<<" with dist= "<<d<<" to
        // heap"<<std::endl;
            faiss::heap_push < faiss::CMax < float, CANDY::VertexPtr >> (++nres, D,
                    I.data(), d, v1);
      } else if (d < D[0]) {
        // std::cout<<"pushing  "<<*v1<<" with dist= "<<d<<" to
        // heap"<<std::endl;
            faiss::heap_replace_top < faiss::CMax < float, CANDY::VertexPtr >> (
                    nres, D, I.data(), d, v1);
      }
      candidates.push(v1, d);
    }

    nstep++;
    if (nstep > efSearch) {
      break;
    }
  }
  // printf("%ld visited\n", visited_vertex);
  return nres;
}
void CANDY::HNSW::neighbor_range(int level, size_t *begin, size_t *end) {
  *begin = cum_nb_neighbors(level);
  *end = cum_nb_neighbors(level + 1);
}
CANDY::VertexPtr greedy_update_nearest(CANDY::HNSW &hnsw,
                                       CANDY::DistanceQueryer &disq, int level,
                                       CANDY::VertexPtr nearest,
                                       float &d_nearest) {
  for (;;) {

    auto prev_nearest = nearest;
    size_t begin;
    size_t end;
    hnsw.neighbor_range(level, &begin, &end);
    // auto neighbors = hnsw.getNeighborsByPtr(nearest);
    auto neighbors = nearest->neighbors;
    for (auto it = neighbors.begin() + begin;
         it != neighbors.end() && it != neighbors.begin() + end &&
         begin < neighbors.size();
         it++) {
      if (*it == nullptr) {
        break;
      }
      // INTELLI_INFO("FINDING NEAREST...");
      auto vertex = *it;
      float dis;
      if(disq.is_search && hnsw.opt_mode_==OPT_LVQ){
          if(vertex->code_final_ == nullptr){
              vertex->code_final_ = disq.compute_code(vertex->id);
          }
          dis = disq(vertex->code_final_);
      } else {
          dis = disq(vertex->id);
      }
      if (dis < d_nearest) {
        d_nearest = dis;
        nearest = vertex;
        // std::cout<<"moving to "<<*nearest<<std::endl;
      }
    }
    //
    //        if(torch::equal(*(nearest->id), *(prev_nearest->id))){
    //            //std::cout<<"nearest vector: "<<*nearest<<std::endl;
    //            INTELLI_INFO("OUT!");
    //            return nearest;
    //        }
    // std::cout<<"prev:"<<*(prev_nearest->id);
    // std::cout<<"new:"<<*(nearest->id);
    auto tensor1 = (*(prev_nearest->id));
    auto tensor2 = (*(nearest->id));
    if (torch::equal(tensor1, tensor2)) {
      return nearest;
    }
    if (prev_nearest == nearest) {
      //            auto same = torch::equal(*(nearest->id),
      //            *(prev_nearest->id)); std::cout<<same<<std::endl;
      //            if(!torch::equal(*(nearest->id), *(prev_nearest->id))){
      //                //std::cout<<"nearest vector: "<<*nearest<<std::endl;
      //                INTELLI_INFO("with different vectors!");
      //            }
      // INTELLI_INFO("OUT from equal ptr!");
      return nearest;
    }
  }
}

void CANDY::HNSW::add_without_lock(CANDY::DistanceQueryer &disq,
                                   int assigned_level, CANDY::VertexPtr pt_id,
                                   CANDY::VisitedTable &vt) {
  auto nearest = entry_point_;
  // update global mean for LVQ
  ntotal += 1;
  if (opt_mode_ == OPT_LVQ) {
    auto new_data = (*(pt_id->id)).contiguous().data_ptr<float>();
    for (int64_t i = 0; i < vecDim_; i++) {
      auto div = (new_data[i] - mean_[i]) / ntotal;
      mean_[i] += div;
    }
  }
  // empty graph
  if (nearest == nullptr) {
    max_level_ = assigned_level;
    entry_point_ = pt_id;
    return;
  }

  // level from which to add neighbors
  int level = max_level_;
  float d_nearest = disq(nearest->id);
  // from top level to greedy search to assigned_level
  disq.set_rank(false);
  for (level = max_level_; level > assigned_level; level--) {
    nearest = greedy_update_nearest(*this, disq, level, nearest, d_nearest);
  }
  // start add neighbors
  //disq.set_rank(true);
  for (level = assigned_level; level >= 0; level--) {
    add_links_starting_from(disq, pt_id, nearest, d_nearest, level, vt);
  }
  if (assigned_level > (int)max_level_) {
    max_level_ = assigned_level;
    entry_point_ = pt_id;
  }
}

void CANDY::HNSW::add_links_starting_from(CANDY::DistanceQueryer &disq,
                                          CANDY::VertexPtr pt_id,
                                          CANDY::VertexPtr nearest,
                                          float d_nearest, int level,
                                          CANDY::VisitedTable &vt) {
  // maxheap to maintain link targets among neighbors of nearest
  std::priority_queue<CANDY::HNSW::NodeDistCloser> link_targets;
  search_neighbors_to_add(*this, disq, link_targets, nearest, d_nearest, level,
                          vt);
  // control size
  int M = nb_neighbors(level);

  hnsw_shrink_neighbor_list(disq, link_targets, M);

  std::vector<CANDY::VertexPtr> neighbors;
  neighbors.reserve(link_targets.size());

  // add links between chosen nearest's chosen neighbors and new query
  while (!link_targets.empty()) {
    auto other_id = link_targets.top().id;
    auto other_vector = (*(other_id->id));
    auto pt_vector = (*(pt_id->id));
    if (torch::equal(other_vector, pt_vector)) {
      link_targets.pop();
      continue;
    }
    // std::cout<< " adding link with " << *other_id<<std::endl;
    add_link(*this, disq, pt_id, other_id, level);
    neighbors.push_back(other_id);
    link_targets.pop();
  }
  // way round
  for (auto nei : neighbors) {
    auto nei_vector = (*(nei->id));
    auto pt_vector = (*(pt_id->id));
    if (torch::equal(nei_vector, pt_vector)) {
      continue;
    }
    add_link(*this, disq, nei, pt_id, level);
  }
}
void add_link(CANDY::HNSW &hnsw, CANDY::DistanceQueryer &disq,
              CANDY::VertexPtr src, CANDY::VertexPtr dest, int level) {
  size_t begin, end;
  // auto nlist = hnsw.getNeighborsByPtr(src);
  auto nlist = src->neighbors;
  disq.set_query(*(src->id));
  if (!nlist.size()) {
    return;
  }
  hnsw.neighbor_range(level, &begin, &end);
  if (begin >= nlist.size()) {
    return;
  }
  // check repeated
  for (auto it = nlist.begin() + begin;
       it != nlist.end() && it != nlist.begin() + end && begin < nlist.size();
       it++) {
    if (*it == nullptr) {
      break;
    }
    auto it_vector = (*((*it)->id));
    auto dest_vector = (*(dest->id));
    if (torch::equal(it_vector, dest_vector)) {
      return;
    }
  }
  // with slots to add link
  if (nlist[end - 1] == nullptr) {
    size_t i = end;
    while (i > begin) {

      if (nlist[i - 1] != nullptr) {
        break;
      }
      i--;
    }

    // hnsw.insertToNeighborsAt(*src, dest, i);
    src->neighbors[i] = dest;
    return;
  }
  // need prune some neighbors
  std::priority_queue<CANDY::HNSW::NodeDistCloser> resultSet;
  resultSet.emplace(disq(dest->id), dest);
  for (auto it = nlist.begin() + begin;
       it != nlist.end() && it != nlist.begin() + end && begin < nlist.size();
       it++) {
    auto nei = *it;
    resultSet.emplace(disq(nei->id), nei);
  }
  // prune neighbors that is farther in the same direction as a previous
  // neighbor
  hnsw_shrink_neighbor_list(disq, resultSet, end - begin);

  size_t i = begin;
  while (resultSet.size()) {
    src->neighbors[i] = resultSet.top().id;
    resultSet.pop();
    i = i + 1;
  }
  while (i < end) {
    src->neighbors[i] = nullptr;
    i = i + 1;
  }
  return;
}
void hnsw_shrink_neighbor_list(
    CANDY::DistanceQueryer &disq,
    std::priority_queue<CANDY::HNSW::NodeDistCloser> &resultSet_prev,
    size_t max_size) {
  if (resultSet_prev.size() < max_size) {
    return;
  }
  std::priority_queue<CANDY::HNSW::NodeDistFarther> resultSet;
  std::vector<CANDY::HNSW::NodeDistFarther> returnList;
  while (resultSet_prev.size() > 0) {
    resultSet.emplace(resultSet_prev.top().dist, resultSet_prev.top().id);
    resultSet_prev.pop();
  }
  // rebuild resultSet_prev from returnList
  shrink_neighbor_list(disq, resultSet, returnList, max_size);
  for (auto node : returnList) {
    resultSet_prev.emplace(node.dist, node.id);
  }
}
void shrink_neighbor_list(
    CANDY::DistanceQueryer &disq,
    std::priority_queue<CANDY::HNSW::NodeDistFarther> &input,
    std::vector<CANDY::HNSW::NodeDistFarther> &output, size_t max_size) {
  while (input.size() > 0) {
    CANDY::HNSW::NodeDistFarther v1 = input.top();
    disq.set_query(*(v1.id->id));
    input.pop();
    float dist_v1_q = v1.dist;
    bool ok = true;
    for (auto v2 : output) {
      float dist_v1_v2 = disq(v2.id->id);
      // v1 not ok if there is a neighbor v2 of v1 that is closer to v1 than v1
      // closer to query to prevent v1 getting kicked out
      if (dist_v1_v2 < dist_v1_q) {
        ok = false;
        break;
      }
    }

    if (ok) {
      output.push_back(v1);
      if (output.size() >= max_size) {
        return;
      }
    }
  }
}

void search_neighbors_to_add(
    CANDY::HNSW &hnsw, CANDY::DistanceQueryer &disq,
    std::priority_queue<CANDY::HNSW::NodeDistCloser> &results,
    CANDY::VertexPtr entry_point, float d_entry_point, int level,
    CANDY::VisitedTable &vt) {
  // use a unbouneded minheap to contain candidates as search sets
  std::priority_queue<CANDY::HNSW::NodeDistFarther> candidates;
  CANDY::HNSW::NodeDistFarther ev(d_entry_point, entry_point);
  candidates.push(ev);
  results.emplace(d_entry_point, entry_point);
  vt.set(entry_point);

  while (!candidates.empty()) {
    // get the nearest candidate
    const CANDY::HNSW::NodeDistFarther &currEv = candidates.top();

    if (currEv.dist > results.top().dist) {
      break;
    }
    auto currNode = currEv.id;
    // std::cout<< "candidates top: "<< *currNode<<std::endl;
    candidates.pop();
    // iterate over neighbors
    size_t begin, end;
    hnsw.neighbor_range(level, &begin, &end);
    // auto neighbors = hnsw.getNeighborsByPtr(currNode);
    auto neighbors = currNode->neighbors;
    // hnsw.printNeighborsByPtr(currNode);
    for (auto it = neighbors.begin() + begin;
         it != neighbors.end() && it != neighbors.begin() + end &&
         begin < neighbors.size();
         it++) {
      auto nodeId = *it;

      if (nodeId == nullptr) {
        break;
      }
      // already visited
      if (vt.get(nodeId)) {
        continue;
      }
      vt.set(nodeId);

      float dis = disq(nodeId->id);
      CANDY::HNSW::NodeDistFarther evE1(dis, nodeId);
      // when results set does not reach efConstruction, append to it with
      // nearer vectors
      if (results.size() < hnsw.efConstruction || results.top().dist > dis) {
        results.emplace(dis, nodeId);
        candidates.emplace(dis, nodeId);
        if (results.size() > hnsw.efConstruction) {
          results.pop();
        }
      }
    }
  }
  vt.advance();
}

int CANDY::HNSW::random_level() {
  double f = rng.rand_float();
  for (size_t level = 0; level < probs_of_layers_.size(); level++) {
    if (f < probs_of_layers_[level]) {
      return level;
    }
    f -= probs_of_layers_[level];
  }
  return probs_of_layers_.size() - 1;
}
void CANDY::HNSW::set_probs(int64_t M, float levelMult) {
  int nn = 0;
  cum_nneighbor_per_level_.push_back(0);
  for (int level = 0;; level++) {
    float prob = exp(-level / levelMult) * (1 - exp(-1 / levelMult));
    if (prob < 1e-9) {
      break;
    }
    probs_of_layers_.push_back(prob);
    if (level == 0) {
      nn += M * 2;
    } else {
      nn += M;
    }
    cum_nneighbor_per_level_.push_back(nn);
  }
}
int CANDY::HNSW::getLevelsByTensor(torch::Tensor &t) {
  return getLevelsByPtr(newTensor(t));
}

int CANDY::HNSW::getLevelsByPtr(INTELLI::TensorPtr idx) {
  //    for(auto it = levels_.begin(); it!=levels_.end(); it++){
  //        if(it->first==nullptr){
  //            continue;
  //        }
  //        if(torch::equal(*(it->first), *idx)){
  //            return it->second;
  //        }
  //    }
  return -1;
}

size_t CANDY::HNSW::nb_neighbors(size_t layer_no) {
  return cum_nneighbor_per_level_[layer_no + 1] -
         cum_nneighbor_per_level_[layer_no];
}
size_t CANDY::HNSW::cum_nb_neighbors(size_t layer_no) {
  return cum_nneighbor_per_level_[layer_no];
}
void CANDY::HNSW::set_nb_neighbors(size_t layer_no, size_t nb) {
  size_t current = nb_neighbors(layer_no);
  for (size_t i = layer_no + 1; i < max_level_; i++) {
    cum_nneighbor_per_level_[i] += nb - current;
  }
}

int CANDY::HNSW::prepare_level_tab(torch::Tensor &x, bool preset_levels,
                                   bool is_NSW) {
  size_t n = x.size(0);
  if (preset_levels) {
    printf("There is preset levels\n");
  } else {
    if (is_NSW) {
      //printf("INITIALIZE AS NSW: ALL ASSIGNED TO BASE LEVEL\n");
      for (size_t i = 0; i < n; i++) {
        levels_[i] = 1;
      }
    } else {
      //printf("INITIALIZE AS HNSW: ASSIGNING LEVELS\n");
      for (size_t i = 0; i < n; i++) {
        int rand_level = random_level();
        if (levels_[i] == -1) {
          levels_[i] = rand_level + 1;
        }
      }
    }
  }

  int max_level = 0;
  if (is_NSW) {
    return max_level;
  }
  for (size_t i = 0; i < n; i++) {
    int assigned_level = levels_[i] - 1;
    if (assigned_level > max_level) {
      max_level = assigned_level;
    }
  }

  return max_level;
}

string CANDY::HNSW::transform_from_tensor(INTELLI::TensorPtr idx) {
  std::stringstream stream;
  torch::save(*idx, stream);
  return stream.str();
}

void CANDY::HNSW::set_mode(CANDY::HNSW::opt_mode_t opt_mode,
                           faiss::MetricType metric) {
  opt_mode_ = opt_mode;
  faissMetric = metric;
  switch (opt_mode) {
  case OPT_VANILLA:
    INTELLI_INFO("NO DISTANCE OPTIMIZATION!");
    break;
  case OPT_LVQ:
    INTELLI_INFO("USING LVQ!");
    break;
  case OPT_DCO:
    INTELLI_INFO("USING DCO!");
    break;
  default:
    INTELLI_ERROR("NO SUCH OPT: USING VANILLA!");
    opt_mode_ = OPT_VANILLA;
  }
  switch (faissMetric) {
  case faiss::METRIC_L2:
    INTELLI_INFO("USING L2 DISTANCE!");
    break;
  case faiss::METRIC_INNER_PRODUCT:
    INTELLI_INFO("USING IP DISTANCE!");
    break;
  default:
    INTELLI_ERROR("NO SUCH METRIC: USING IP!");
    faissMetric = faiss::METRIC_INNER_PRODUCT;
  }
}
