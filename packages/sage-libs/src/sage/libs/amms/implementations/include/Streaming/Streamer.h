//
// Created by haolan on 8/7/23.
//

#ifndef INTELLISTREAM_STREAMER_H
#define INTELLISTREAM_STREAMER_H

#include <Parallelization/BlockPartitionRunner.h>

namespace LibAMM {
class Streamer {
 protected:
  LibAMM::TensorPtr matC = nullptr;
  INTELLI::ConfigMapPtr metrics;
 public:
  Streamer() {}

  ~Streamer() {}

  torch::Tensor run(INTELLI::ConfigMapPtr cfg,
                    torch::Tensor A,
                    torch::Tensor B,
                    uint64_t sketchSize = 1,
                    string metricPrefix = "");
  /**
   * @return all the running metrics as a ConfigMap
   */
  INTELLI::ConfigMapPtr getMetrics() {
    return metrics;
  }
};
} // LibAMM
#endif //INTELLISTREAM_STREAMER_H
