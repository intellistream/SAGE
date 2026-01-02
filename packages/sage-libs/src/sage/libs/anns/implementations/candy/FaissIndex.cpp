//
// Created by Isshin on 2024/1/30.
//
#include <FaissIndex.h>
#include <faiss/IndexHNSW.h>
#include <faiss/IndexIVFPQ.h>
#include <faiss/IndexPQ.h>
#include <faiss/IndexNNDescent.h>
#include <faiss/IndexLSH.h>
#include <faiss/IndexNSG.h>
#include <faiss/IndexVanama.h>
#include <faiss/IndexMNRU.h>
#include <faiss/IndexNSW.h>

bool CANDY::FaissIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractIndex::setConfig(cfg);
  INTELLI_INFO("SETTING CONFIG FOR FaissIndex");
  std::string metricType = cfg->tryString("metricType", "IP", true);
  vecDim = cfg->tryI64("vecDim", 768, true);
  index_type = cfg->tryString("faissIndexTag", "flat", true);
  auto bytes = cfg->tryI64("encodeLen", 1, true);
  INTELLI_INFO("USING " + metricType + " AS METRIC");
  if (index_type == "flat") {
    INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE FLAT");
    index = new faiss::IndexFlat(vecDim, faissMetric);
  } else if (index_type == "HNSW") {
    INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE HNSWFlat");
    auto M = cfg->tryI64("maxConnection", 32, true);
    index = new faiss::IndexHNSWFlat(vecDim, M, faissMetric);
  } else if (index_type == "Vanama") {
      INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE VanamaFlat");
      auto M = cfg->tryI64("maxConnection", 32, true);
      index = new faiss::IndexVanamaFlat(vecDim, M, faissMetric);
  } else if (index_type == "MNRU") {
      INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE MNRUFlat");
      auto M = cfg->tryI64("maxConnection", 32, true);
      index = new faiss::IndexMNRUFlat(vecDim, M, faissMetric);
  } else if (index_type == "NSW") {
      INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE NSWFlat");
      auto M = cfg->tryI64("maxConnection", 32, true);
      index = new faiss::IndexNSWFlat(vecDim, M, faissMetric);
  } else if (index_type == "PQ") {
    INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE PQ");
    // number of bits in PQ
    auto nbits = cfg->tryI64("encodeLenBits", bytes * 8, true);
    bool is_online = cfg->tryI64("isOnlinePQ", 0, true);
    if (is_online == 1) {
      INTELLI_INFO("INITIALIZE AS ONLINE PQ!");
    }
    // number of subquantizers in PQ
    auto M = cfg->tryI64("subQuantizers", 8, true);

    if (vecDim == 420 || vecDim == 100) {
      index = new faiss::IndexPQ(is_online, vecDim + 4, M, nbits, faissMetric);
    } else if (vecDim == 1369) {
      index = new faiss::IndexPQ(is_online, vecDim + 7, M, nbits, faissMetric);
    } else {
      index = new faiss::IndexPQ(is_online, vecDim, M, nbits, faissMetric);
    }
  } else if (index_type == "IVFPQ") {
    INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE IVFPQ");
    auto nlist = cfg->tryI64("nlist", 1000, true);
    auto M = cfg->tryI64("subQuantizers", 8, true);
    auto nbits = cfg->tryI64("encodeLenBits", bytes * 8, true);
    // Hard-coded for msong and glove
    if (vecDim == 420 || vecDim == 100) {
      faiss::IndexFlat *quantizer = new faiss::IndexFlat(vecDim + 4, faissMetric);
      index = new faiss::IndexIVFPQ(quantizer, vecDim + 4, nlist, M, nbits);
    } else if (vecDim == 1369) {
      faiss::IndexFlat *quantizer = new faiss::IndexFlat(vecDim + 7, faissMetric);
      index = new faiss::IndexIVFPQ(quantizer, vecDim + 7, nlist, M, nbits);
    } else {
      faiss::IndexFlat *quantizer = new faiss::IndexFlat(vecDim, faissMetric);
      index = new faiss::IndexIVFPQ(quantizer, vecDim, nlist, M, nbits);
    }
  } else if (index_type == "NNDescent") {
    INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE NNDescent");
    auto K = cfg->tryI64("K", 5, true);
    index = new faiss::IndexNNDescentFlat(vecDim, K);
  } else if (index_type == "LSH") {

    auto nbits = cfg->tryI64("encodeLenBits", bytes * 32, true);
    index = new faiss::IndexLSH(vecDim, nbits, faissMetric, true, true);
    //index = new faiss::IndexLSH(vecDim, nbits,true,true);
  } else if (index_type == "NSG") {
    INTELLI_INFO("ENCAPSULATED FAISS INDEX: USE NSG");
    auto R = cfg->tryI64("R", 32, true);
    index = new faiss::IndexNSGFlat(vecDim, R);
  } else {
    INTELLI_INFO("NOT AN ENCAPSULATED FAISS INDEX: USE FLAT AS DEFAULT");
    index = new faiss::IndexFlat(vecDim, faissMetric);
  }
  index->set_verbose(true);
  dbTensor = torch::zeros({0, vecDim});
  lastNNZ = -1;
  expandStep = 100;
  return true;
}

bool CANDY::FaissIndex::loadInitialTensor(torch::Tensor &t) {

  // normalize the tensor before insert
  if (metricType == "cossim") {
    t = t / (torch::sqrt(torch::sum(t * t, 1)).view({t.size(0), 1}));
  }

  auto n = t.size(0);
  float *new_data = t.contiguous().data_ptr<float>();
  isFaissTrained = true;
  if (index_type == "IVFPQ" || index_type == "PQ") {
    INTELLI_INFO("IMCOMPATIBLE DIMENSIONS: PADDING ZEROS FOR PQ and IVFPQ");
    if (vecDim == 100 || vecDim == 420) {

      auto t_temp = torch::concat({t, torch::zeros({n, 4})}, 1);
      //t_temp.slice(1,t_temp.size(1)-4,t_temp.size(1)) -= t_temp.slice(1,t_temp.size(1)-4, t_temp.size(1));
      t_temp = t_temp.nan_to_num(0.0);
      t_temp = t_temp.contiguous();
      float *new_data_padding = t_temp.data_ptr<float>();

      INTELLI_INFO("Start training");
      index->train(n, new_data_padding);

      INTELLI_INFO("FINISH TRAINING");
      index->add(n, new_data_padding);

      INTELLI_INFO("FINISH ADDING");

      return true;
    } else if (vecDim == 1369) {
      auto t_temp = torch::concat({t, torch::zeros({n, 7})}, 1);
      t_temp = t_temp.nan_to_num(0.0);
      float *new_data_padding = t_temp.data_ptr<float>();

      INTELLI_INFO("Start training");
      index->train(n, new_data_padding);

      INTELLI_INFO("FINISH TRAINING");
      index->add(n, new_data_padding);
      INTELLI_INFO("FINISH ADDING");
      return true;
    }
  }

  INTELLI_INFO("Start training");
  index->train(n, new_data);

  INTELLI_INFO("FINISH TRAINING");
  std::cout << "tiny wait" << std::endl;
  index->add(n, new_data);
  INTELLI_INFO("FINISH ADDING");
  if (index_type == "IVFPQ" || index_type == "PQ" || index_type == "LSH") {
    return true;
  } else {
    return true;
  }

}
bool CANDY::FaissIndex::insertTensor(torch::Tensor &t) {
  // normalize the tensor before insert
  if (metricType == "cossim") {
    t = t / (torch::sqrt(torch::sum(t * t, 1)).view({t.size(0), 1}));
  }
  if (!isFaissTrained) {
    loadInitialTensor(t);
    isFaissTrained = true;
    return false;
  }
  float *new_data = t.contiguous().data_ptr<float>();
  auto n = t.size(0);
  if (index_type == "IVFPQ" || index_type == "PQ") {
    if (vecDim == 100 || vecDim == 420) {
      auto t_temp = torch::zeros({n, vecDim + 4});
      t_temp.slice(1, 0, vecDim) = t;

      t_temp = t_temp.nan_to_num(0.0);
      float *new_data_padding = t_temp.contiguous().data_ptr<float>();
      index->add(n, new_data_padding);
      return true;
    } else if (vecDim == 1369) {
      auto t_temp = torch::zeros({n, vecDim + 7});
      t_temp.slice(1, 0, vecDim) = t;
      std::cout << "inserting" << std::endl;

      t_temp = t_temp.nan_to_num(0.0);
      float *new_data_padding = t_temp.contiguous().data_ptr<float>();
      index->add(n, new_data_padding);
      return true;
    }
  }
  if (index_type == "IVFPQ" || index_type == "PQ" || index_type == "LSH") {
    index->add(n, new_data);
    //return INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &t, &lastNNZ, expandStep);
    return true;
  } else {
    index->add(n, new_data);
    //should be unneeded
//INTELLI::IntelliTensorOP::appendRowsBufferMode(&dbTensor, &t, &lastNNZ, expandStep);
    return true;
  }
}
std::vector<faiss::idx_t> CANDY::FaissIndex::searchIndexParam(torch::Tensor q, int64_t k, int64_t param){
    if(index_type=="HNSW") {
        auto indexHNSW = static_cast<faiss::IndexHNSW *>(index);
        indexHNSW->hnsw.efSearch = param;
    } else if(index_type=="MNRU") {
        auto indexMNRU = static_cast<faiss::IndexMNRU *>(index);
        indexMNRU->main_index.efSearch = param;
        indexMNRU->backup_index.efSearch = param;
    }

    return searchIndex(q,k);

}
std::vector<faiss::idx_t> CANDY::FaissIndex::searchIndex(torch::Tensor q, int64_t k) {

  auto queryData = q.contiguous().data_ptr<float>();
	std::cout<<"tiny wait"<<std::endl;
 int64_t querySize = q.size(0);

  if (index_type == "IVFPQ" || index_type == "PQ") {
    INTELLI_INFO("IMCOMPATIBLE DIMENSIONS: PADDING ZEROS FOR PQ and IVFPQ");
    if (vecDim == 100 || vecDim == 420) {
      auto q_temp = torch::zeros({querySize, vecDim + 4});
      q_temp.slice(1, 0, vecDim) = q;
      q_temp = q_temp.nan_to_num(0.0);
      auto queryData_padding = q_temp.contiguous().data_ptr<float>();
	std::cout<<"tiny wait"<<std::endl;
      std::vector<faiss::idx_t> ru(k * querySize);
      std::vector<float> distance(k * querySize);
      index->search(querySize, queryData_padding, k, distance.data(), ru.data());
      return ru;
    } else if (vecDim == 1369) {
      auto q_temp = torch::zeros({querySize, vecDim + 7});
      q_temp.slice(1, 0, vecDim) = q;
      std::cout << "tiny wait" << std::endl;
      q_temp = q_temp.nan_to_num(0.0);
      auto queryData_padding = q_temp.contiguous().data_ptr<float>();
      std::vector<faiss::idx_t> ru(k * querySize);
      std::vector<float> distance(k * querySize);
      index->search(querySize, queryData_padding, k, distance.data(), ru.data());
      return ru;
    }
  }

  std::vector<faiss::idx_t> ru(k * querySize);
  std::vector<float> distance(k * querySize);
  index->search(querySize, queryData, k, distance.data(), ru.data());
  return ru;
}

std::vector<torch::Tensor> CANDY::FaissIndex::searchTensor(torch::Tensor &q, int64_t k) {
  auto idx = searchIndex(q, k);
  return getTensorByIndex(idx, k);
}

std::vector<torch::Tensor> CANDY::FaissIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k) {
  int64_t size = idx.size() / k;
  std::vector<torch::Tensor> ru(size);
  for (int64_t i = 0; i < size; i++) {
    ru[i] = torch::zeros({k, vecDim});
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = idx[i * k + j];
      //printf("%ld%ld=%ld\n", i,j,tempIdx);
      float tempSlice[vecDim];
//            if(index_type=="FaissIVFPQ" || index_type == "FaissPQ"){
//                if(vecDim=100 || vecDim == 420){
//
//                } else if (vecDim==1369){
//
//                }
//            }
          index->reconstruct(tempIdx, tempSlice);
          auto tempTensor = torch::from_blob(tempSlice, {1, vecDim});
          if (tempIdx >= 0) { ru[i].slice(0, j, j + 1) = tempTensor; };


    }
  }
  return ru;
}
