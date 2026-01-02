//
// Created by Isshin on 2024/1/18.
//

#ifndef CANDY_DISTANCEQUERYER_H
#define CANDY_DISTANCEQUERYER_H
#include <Utils/IntelliTensorOP.hpp>
#include <faiss/MetricType.h>
#include <faiss/utils/distances.h>
#include <cmath>
#include <CANDY/HNSWNaive/AdSampling.h>
#define OPT_VANILLA 0
#define OPT_LVQ 1
#define OPT_DCO 2
namespace CANDY {
/**
 * @class
 * @brief a counterpart of faiss::DistanceComputer, but more lightweight. Does
 * not depend on storage index to re-build data.
 */
class DistanceQueryer {
public:
  typedef int64_t opt_mode_t;
  opt_mode_t opt_mode_ = OPT_VANILLA;
  faiss::MetricType faissMetric = faiss::METRIC_L2;
  size_t d_;
  torch::Tensor query_;

  float *data_;

  /// used for LVQ
  std::vector<float> *mean_;
  bool is_rank = false;
  bool is_search = false;
  int8_t *code_ = nullptr;
  float delta_query_ = 0.0;

  /// used for AdSAMPLING
  AdSampling* ads = nullptr;
  torch::Tensor transformed;

  explicit DistanceQueryer(size_t d)
      : d_(d){

        };
  DistanceQueryer() = default;
  /**
   * @brief compute the distance between given idx's vector and query vector
   * @param idx the target vector to be computed with query vector
   * @return L2 Distance
   */
  float operator()(INTELLI::TensorPtr idx) {
      // we always build using vanilla
    if (opt_mode_ == OPT_VANILLA || !is_search || (opt_mode_ == OPT_DCO && !is_rank)) {
      auto idx_data = (*idx).contiguous().data_ptr<float>();
      if (faissMetric == faiss::METRIC_L2) {
        return fvec_L2(data_, idx_data, d_);
      } else {
        return -fvec_IP(data_, idx_data, d_);
      }
    }
    if (opt_mode_ == OPT_LVQ) {
      auto idx_data = (*idx).contiguous().data_ptr<float>();
      int8_t* first_codes_idx = new int8_t[d_];
      int8_t* first_codes_query = code_;
      //float delta_idx = lvq_first_level(idx_data, d_, first_codes_idx);
      //float delta_query = delta_query_;
      lvq_first_level(idx_data, d_, first_codes_idx);

      // during ranking, need to compute residual codes (second-level lvq)
      if(is_rank){
//          int8_t* second_codes_idx = new int8_t[d_];
//          int8_t* second_codes_query = new int8_t[d_];
//          lvq_second_level(idx_data, d_, second_codes_idx, delta_idx);
//          lvq_second_level(data_, d_, second_codes_query, delta_query);
//          for(size_t i=0; i<d_; i++){
//              first_codes_idx[i]+=second_codes_idx[i];
//              first_codes_query[i] += second_codes_query[i];
//          }
//          free(second_codes_idx);
//          free(second_codes_query);
      }
      if (faissMetric == faiss::METRIC_L2) {
          auto dist =  int8vec_L2(first_codes_idx, first_codes_query, d_);
          free(first_codes_idx);
          //free(first_codes_query);
          return dist;
      } else {
        auto dist = int8vec_IP(first_codes_idx, first_codes_query, d_);
        free(first_codes_idx);
        //free(first_codes_query);
        return -dist;
      }
    }
    if(opt_mode_ == OPT_DCO && is_rank){
        if(faissMetric == faiss::METRIC_L2){
            //assert(ads);
            //std::cout<< "this query"<<transformed;
            //std::cout<<"to saerch"<<*idx;
            auto dist = ads->distanceCompute_L2(transformed, *idx);
            return dist;
        } else {
            printf("ADSAMPLING DOES NOT SUPPORT INNER PRODUCT!\n");
        }
    }
    return 0;
  }

  float operator()(const int8_t* code){
      if(opt_mode_ == OPT_LVQ){
          if(faissMetric == faiss::METRIC_L2){
              auto dist = int8vec_L2(code_, code, d_);
              return dist;
          } else {
              auto dist = int8vec_IP(code_, code, d_);
              return -dist;
          }
      }
      return 0;
  }
  float lvq_first_level(const float* x, const size_t len, int8_t* codes){
    assert(mean_);
    size_t min_index =0;
    size_t max_index =0;
    float min = x[min_index] - (*mean_)[min_index];
    float max = x[max_index] - (*mean_)[max_index];

    for(size_t i=1; i<len; i++){
        if(x[i]-(*mean_)[i]<min){
            min_index = i;
            min = x[i] - (*mean_)[i];
        } else if(x[i] - (*mean_)[i]>max){
            max_index = i;
            max = x[i] - (*mean_)[i];
        }
    }

    float u = max;
    float l = min;

    float delta = (u-l)/(pow(2.0, 8)-1);
    for(size_t i=0; i<len; i++){
        float temp = (delta * (std::floor((x[i]-(*mean_)[i]-l)/delta)+0.5) +l);
        codes[i] = (int)(0xff*temp);
    }
    return delta;

  }

  void lvq_second_level(const float*x, const size_t len, int8_t* codes, float delta){
      assert(mean_);

      float u = delta/2;
      float l = -delta/2;

      float delta_second = (u-l)/(pow(2.0, 8)-1);
      for(size_t i=0; i<len; i++){
          float temp = (delta_second * (std::floor((x[i]-l)/delta_second)+0.5) +l);
          codes[i] = (int)(0xff*temp);
      }
      return;

  }

  float symmetric_dis(INTELLI::TensorPtr i, INTELLI::TensorPtr j) {
    if (opt_mode_ == OPT_VANILLA) {
      auto i_data = (*i).contiguous().data_ptr<float>();
      auto j_data = (*j).contiguous().data_ptr<float>();
      if (faissMetric == faiss::METRIC_L2) {
        return fvec_L2(i_data, j_data, d_);
      } else {
        return -fvec_IP(i_data, j_data, d_);
      }
    }
    if (opt_mode_ == OPT_LVQ) {
      auto i_data = (*i).contiguous().data_ptr<float>();
      auto j_data = (*j).contiguous().data_ptr<float>();
      int8_t* first_codes_i = new int8_t[d_];
      int8_t* first_codes_j = new int8_t[d_];
      //float delta_i = lvq_first_level(i_data, d_, first_codes_i);
      //float delta_j = lvq_first_level(j_data, d_, first_codes_j);
      lvq_first_level(i_data, d_, first_codes_i);
      lvq_first_level(j_data, d_, first_codes_j);
      if(is_rank){
//          int8_t* second_codes_i = new int8_t[d_];
//          int8_t* second_codes_j = new int8_t[d_];
//          lvq_second_level(i_data, d_, second_codes_i, delta_i);
//          lvq_second_level(j_data, d_, second_codes_j, delta_j);
//          for(size_t i=0; i<d_; i++){
//              first_codes_i[i]+=second_codes_i[i];
//              first_codes_j[i]+=second_codes_j[i];
//          }
//          free(second_codes_i);
//          free(second_codes_j);
      }
      if (faissMetric == faiss::METRIC_L2) {

        auto dist = int8vec_L2(first_codes_i, first_codes_j, d_);
        free(first_codes_i);
        free(first_codes_j);
        return dist;
      } else {
          auto dist = int8vec_IP(first_codes_i, first_codes_j, d_);
          free(first_codes_i);
          free(first_codes_j);
          return -dist;
      }
    }
    if(opt_mode_ == OPT_DCO){
        if(faissMetric == faiss::METRIC_L2){
            assert(ads);
            auto dist = ads->distanceCompute_L2(*i, *j);
            return dist;
        } else {
            printf("ADSAMPLING DOES NOT SUPPORT INNER PRODUCT!\n");
        }
    }
    return 0;
  }

  void set_query(torch::Tensor &x) {
    query_ = x;
    data_ = (query_).contiguous().data_ptr<float>();
    if(opt_mode_ == OPT_LVQ){
        if(code_!=nullptr){
            free(code_);
        }
        code_ = new int8_t[d_];
        delta_query_ = lvq_first_level(data_, d_, code_);
    }
  }

  int8_t* compute_code(INTELLI::TensorPtr idx){
      auto data = (*idx).contiguous().data_ptr<float>();
      int8_t* codes = new int8_t[d_];
      lvq_first_level(data, d_, codes);
      return codes;
  }

  torch::Tensor compute_transformed(INTELLI::TensorPtr idx){
      assert(ads);
      return ads->transform(*idx);
  }

  void set_mode(opt_mode_t opt_mode, faiss::MetricType metric) {
    opt_mode_ = opt_mode;
    faissMetric = metric;
    if(opt_mode_ == OPT_DCO){
        ads = new AdSampling(d_);
    }
  }

  void set_rank(bool rank){
      is_rank = rank;
  }

  void set_search(bool search){
      is_search = search;
  }

  float int8vec_IP(const int8_t *x, const int8_t *y, size_t d) {
    int32_t product = 0;
    for (size_t i = 0; i < d; i++) {
      product += (int32_t)(x[i] * y[i]);
    }
    return (float)(product);
  }

  float fvec_IP(const float* x, const float* y,size_t d){
      float product = 0;
      for(size_t i=0; i<d; i++){
          product += x[i] * y[i];
      }
      return product;
  }

  float int8vec_L2(const int8_t *x, const int8_t *y, size_t d) {
    int32_t sum = 0;
    for (size_t i = 0; i < d; i++) {
      sum += (int32_t)((x[i] - y[i]) * (x[i] - y[i]));
    }
    return (float)(sum);
  }

  float fvec_L2(const float *x, const float *y, size_t d){
      float sum = 0;
      for(size_t i=0;i<d; i++){
          sum += (x[i]-y[i])*(x[i]-y[i]);
      }
      return sum;
  }

  //    int8_t* lvq_encode(const float *x, const float *mean, size_t d) {
  //
  //        return nullptr;
  //    }
};
} // namespace CANDY

#endif // CANDY_DISTANCEQUERYER_H
