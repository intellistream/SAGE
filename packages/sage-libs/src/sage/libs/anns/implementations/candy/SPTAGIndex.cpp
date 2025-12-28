/*! \file SPTAGIndex.cpp*/
//
// Created by tony on 25/05/23.
//

#include <SPTAGIndex.h>
#include <Utils/UtilityFunctions.h>
#include <time.h>
#include <chrono>
#include <assert.h>

bool CANDY::SPTAGIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  FlatIndex::setConfig(cfg);
    sptag = SPTAG::VectorIndex::CreateInstance(SPTAG::IndexAlgoType::BKT,
                                               SPTAG::VectorValueType::Float);
  if(faissMetric == faiss::METRIC_INNER_PRODUCT) {
    INTELLI_INFO("Using inner product for SPTAG");
    sptag->SetParameter("DistCalcMethod", SPTAG::Helper::Convert::ConvertToString(SPTAG::DistCalcMethod::InnerProduct));
  }
  else {
    INTELLI_INFO("Using l2 for SPTAG");
      sptag->SetParameter("DistCalcMethod", SPTAG::Helper::Convert::ConvertToString(SPTAG::DistCalcMethod::L2));
  }
  SPTAGThreads = cfg->tryI64("SPTAGThreads",1,false);
  SPTAGNumberOfInitialDynamicPivots = cfg->tryI64("SPTAGNumberOfInitialDynamicPivots",32,false);
  SPTAGMaxCheck = cfg->tryI64("SPTAGMaxCheck",8192,false);
  SPTAGGraphNeighborhoodSize =  cfg->tryI64("SPTAGGraphNeighborhoodSize",32,false);
  SPTAGGraphNeighborhoodScale = cfg->tryDouble("SPTAGGraphNeighborhoodScale",2.0,false);
  SPTAGRefineIterations = cfg->tryI64("SPTAGRefineIterations",3,false);
  sptag->SetParameter("NumberOfThreads", std::to_string(SPTAGThreads));
  sptag->SetParameter("NumberOfInitialDynamicPivots", std::to_string(SPTAGNumberOfInitialDynamicPivots));
  sptag->SetParameter("MaxCheck", std::to_string(SPTAGMaxCheck));
  sptag->SetParameter("GraphNeighborhoodSize", std::to_string(SPTAGGraphNeighborhoodSize));
  sptag->SetParameter("GraphNeighborhoodScale", std::to_string(SPTAGGraphNeighborhoodScale));
  sptag->SetParameter("RefineIterations", std::to_string(SPTAGRefineIterations));
  isInitialized = false;
  return true;
}
void CANDY::SPTAGIndex::reset() {
  lastNNZ = -1;
  isInitialized = false;
  sptag.reset();
}
bool CANDY::SPTAGIndex::loadInitialTensor(torch::Tensor &t) {
  FlatIndex::insertTensor(t);
  isInitialized = true;
  int64_t num_vectors = t.size(0);
  float *dbData = t.contiguous().data_ptr<float>();
  // Insert new vectors into the SPTAG index

  sptag->BuildIndex(dbData,num_vectors,vecDim);

  return true;
}
bool CANDY::SPTAGIndex::insertTensor(torch::Tensor &t) {
  FlatIndex::insertTensor(t);
  int64_t num_vectors = t.size(0);
  float *dbData = t.contiguous().data_ptr<float>();
  // Insert new vectors into the SPTAG index
  sptag->AddIndex(dbData,num_vectors,vecDim,nullptr);
  return true;
}


std::vector<torch::Tensor> CANDY::SPTAGIndex::searchTensor(torch::Tensor &q, int64_t k) {
  int64_t num_queries = q.size(0);
  std::vector<torch::Tensor> ru(num_queries);
  int64_t dim = q.size(1);
  for (int64_t i = 0; i < num_queries; ++i) {
    ru[i]=  torch::zeros({k, vecDim});
    auto  rowI = q.slice(0,i,i+1).contiguous();
    float  *queryRaw = rowI.data_ptr<float>();
    // Prepare query result container for SPTAG
    SPTAG::QueryResult query_result(queryRaw, k, true);
    // Perform the search for the i-th query vector
    sptag->SearchIndex(query_result);
    // Store the result indices in the output tensor
    for (int64_t j = 0; j < k; ++j) {
      auto tempIdx = query_result.GetResult(j)->VID;
        printf("%ld%ld=%ld\n", i,j,tempIdx);
      ru[i].slice(0, j, j + 1) = dbTensor.slice(0, tempIdx, tempIdx + 1);
    }
  }
  return ru;
}
