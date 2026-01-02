//
// Created by Isshin on 2024/5/31.
//
#include <LSHAPGIndex.h>
int _lsh_UB=0;
int _G_COST=0;
int _g_dist_mes=0;
namespace CANDY{
bool LSHAPGIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  if(this->faissMetric==faiss::METRIC_INNER_PRODUCT) {
    _g_dist_mes=1;
    INTELLI_INFO("switch into inner product");
  } else {
      _g_dist_mes=0;
    INTELLI_INFO("switch back to L2");
  }
  vecDim = cfg->tryI64("vecDim", 768, true);
  flatBuffer.setConfig(cfg);
  return true;
}
bool  LSHAPGIndex::loadInitialTensor(torch::Tensor &t) {

  prep=Preprocess(vecDim);

  auto tc=t.clone();
  prep.load_data(tc);
  Parameter param1(prep, L, K, 1.0f);
  divG = new divGraph(prep, param1, T, efC, pC, pQ);
  flatBuffer.loadInitialTensor(t);
  return true;
}


std::vector<faiss::idx_t> CANDY::LSHAPGIndex::searchIndex(torch::Tensor q, int64_t k){
    auto querySize = q.size(0);
    auto query_data = q.contiguous().data_ptr<float>();
    prep.set_query(query_data, q.size(0));
    if(divG) divG->ef = k+150;

    std::string f1 = "divgraph";
    std::string f2="fold";
    auto results = search_candy(c,k,divG,prep,beta,2);
    //unsigned num0 = results[0].res.size();
    //printf(" result size %d\n", num0);
    //printf("results:\n");
    std::vector<faiss::idx_t> ru(k*querySize);
    //printf("result set size :%lu\n",results.size());
    for(int i=0; i<querySize; i++) {
        auto res=results[i];
        //printf("query result size: %lu\n",res->res.size());
        for(int j=0; j<k; j++) {
            ru[i*k+j]=res->res[j].id;
        }
    }
    return ru;

}

std::vector<torch::Tensor> CANDY::LSHAPGIndex::searchTensor(torch::Tensor &q, int64_t k){
    auto idx = searchIndex(q,k);
    return getTensorByIndex(idx,k);

}

std::vector<torch::Tensor> CANDY::LSHAPGIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k){
    int64_t size = idx.size() / k;
	auto dbTensor=flatBuffer.rawData();
    std::vector<torch::Tensor> ru(size);
    for (int64_t i = 0; i < size; i++) {
        ru[i] = torch::zeros({k, vecDim});
        for (int64_t j = 0; j < k; j++) {
            int64_t tempIdx = idx[i * k + j];

            if (tempIdx >= 0) {
                ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1);

            };
        }
    }
    return ru;

}
bool LSHAPGIndex::insertTensor(torch::Tensor &t) {
  auto tc=t.clone();
  divG->appendTensor(tc,&prep);
  flatBuffer.insertTensor(t);
  return true;
}

}
