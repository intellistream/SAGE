/*! \file UtilityFunctions.hpp*/
// Copyright (C) 2021 by the INTELLI team (https://github.com/intellistream)

#ifndef IntelliStream_SRC_UTILS_UTILITYFUNCTIONS_HPP_
#define IntelliStream_SRC_UTILS_UTILITYFUNCTIONS_HPP_

#include <string>
#include <experimental/filesystem>
#include <barrier>
#include <functional>
//#include <torch/torch.h>
//#include <ATen/ATen.h>
//#include <Common/Types.h>
#include <Utils/IntelliTimeStampGenerator.h>
#include <Utils/IntelliTensorOP.hpp>
#include <vector>
#include <torch/torch.h>
#include <filesystem>
/* Period parameters */

#define TRUE 1
#define FALSE 0

#include <sys/time.h>

namespace INTELLI {
typedef std::shared_ptr<std::barrier<>> BarrierPtr;
#define TIME_LAST_UNIT_MS 1000
#define TIME_LAST_UNIT_US 1000000
#define chronoElapsedTime(start) std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::high_resolution_clock::now() - start).count()
/**
 * @defgroup
 */
class UtilityFunctions {

 public:
  UtilityFunctions();

  //static std::shared_ptr<std::barrier<>> createBarrier(int count);

  // static void timerStart(Result &result);

  //static void timerEnd(Result &result);

  static size_t timeLast(struct timeval past, struct timeval now);

  static size_t timeLastUs(struct timeval past);

  //bind to CPU
  /*!
   bind to CPU
   \li bind the thread to core according to id
   \param id the core you plan to bind, -1 means let os decide
   \return cpuId, the real core that bind to

    */
  static int bind2Core(int id);
  //partition

  static std::vector<size_t> avgPartitionSizeFinal(size_t inS, std::vector<size_t> partitionWeight);

  static std::vector<size_t> weightedPartitionSizeFinal(size_t inS, std::vector<size_t> partitionWeight);

  static size_t to_periodical(size_t val, size_t period) {
    if (val < period) {
      return val;
    }
    size_t ru = val % period;
    /* if(ru==0)
     {
       return  period;
     }*/
    return ru;
  }
  /**
   * @brief get the latency percentile from a time stamp vector
   * @param fraction the percentile in 0~1
   * @param myTs the time stamp vector
   * @return the latency value
   */
  static double getLatencyPercentage(double fraction, std::vector<INTELLI::IntelliTimeStampPtr> &myTs) {
    size_t rLen = myTs.size();
    size_t nonZeroCnt = 0;
    std::vector<uint64_t> validLatency;
    for (size_t i = 0; i < rLen; i++) {
      if (myTs[i]->processedTime >= myTs[i]->arrivalTime && myTs[i]->processedTime != 0) {
        validLatency.push_back(myTs[i]->processedTime - myTs[i]->arrivalTime);
        nonZeroCnt++;
      }
    }
    if (nonZeroCnt == 0) {
      INTELLI_ERROR("No valid latency, maybe there is no AMM result?");
      return 0;
    }
    std::sort(validLatency.begin(), validLatency.end());
    double t = nonZeroCnt;
    t = t * fraction;
    size_t idx = (size_t) t + 1;
    if (idx >= validLatency.size()) {
      idx = validLatency.size() - 1;
    }
    return validLatency[idx];
  }
  /**
    * @brief save the time stamps to csv file
    * @param fname the name of output file
    * @param myTs the time stamp vector
    * @param skipZero whether skip zero time
    * @return whether the output is successful
    */
  static bool saveTimeStampToFile(std::string fname,
                                  std::vector<INTELLI::IntelliTimeStampPtr> &myTs,
                                  bool skipZero = true) {
    ofstream of;
    of.open(fname);
    if (of.fail()) {
      return false;
    }
    of << "eventTime,arrivalTime,processedTime\n";
    size_t rLen = myTs.size();
    for (size_t i = 0; i < rLen; i++) {
      if (skipZero && myTs[i]->processedTime == 0) {

      } else {
        auto tp = myTs[i];
        string line = to_string(tp->eventTime) + ","
            + to_string(tp->arrivalTime) + "," + to_string(tp->processedTime) + "\n";
        of << line;
      }

    }
    of.close();
    return true;
  }
  static bool existRow(torch::Tensor base, torch::Tensor row) {
    for (int64_t i = 0; i < base.size(0); i++) {
      auto tensor1 = base[i].contiguous();
      auto tensor2 = row.contiguous();
      //std::cout<<"base: "<<tensor1<<std::endl;
      //std::cout<<"query: "<<tensor2<<std::endl;
      if (torch::equal(tensor1, tensor2)) {
        return true;
      }
    }
    return false;
  }
  /** @brief calculate the recall by comparing with ground truth
   * @param groundTruth The ground truth
   * @param prob The tensor result to be validated
   * @return the recall in 0~1
   */
  static double calculateRecall(std::vector<torch::Tensor> groundTruth, std::vector<torch::Tensor> prob) {
    int64_t truePositives = 0;
    int64_t falseNegatives = 0;
    for (size_t i = 0; i < prob.size(); i++) {
      auto gdI = groundTruth[i];
      auto probI = prob[i];
      for (int64_t j = 0; j < probI.size(0); j++) {
        if (existRow(gdI, probI[j])) {
          truePositives++;
        } else {
          falseNegatives++;
        }
      }
    }
    double recall = static_cast<double>(truePositives) / (truePositives + falseNegatives);
    return recall;
  }
  /**
  * @brief convert a list of tensors to a folder with multiple flat binary form files, i.e., <rows> <cols> <flat data> for each
  * @param A the list of tensors
   * @param folderName the name of folder
   * @note this will overwrite the whole folder!
  * @return  bool, the output is successful or not
  */
  static bool tensorListToFile(std::vector<torch::Tensor> &tensorVec, std::string folderName) {
    try {
      std::filesystem::remove_all(folderName);
    } catch (const std::filesystem::filesystem_error &e) {
    }
    try {
      // Create the folder
      std::filesystem::create_directory(folderName);
    } catch (const std::filesystem::filesystem_error &e) {

    }

    for (size_t i = 0; i < tensorVec.size(); i++) {
      std::string fileName = folderName + "/" + std::to_string(i) + ".rbt";
      IntelliTensorOP::tensorToFile(&tensorVec[i], fileName);
    }
    return true;
  }
  /**
  * @brief convert a list of tensors to a folder with multiple flat binary form files, i.e., <rows> <cols> <flat data> for each
   * @param folderName the name of folder
   * @param tensors the number of tensors to be loaded
   * @note this will overwrite the whole folder!
  * @return  the vector of tensors
  */
  static std::vector<torch::Tensor> tensorListFromFile(std::string folderName, uint64_t tensors) {

    std::vector<torch::Tensor> ru((size_t) tensors);
    for (uint64_t i = 0; i < tensors; i++) {
      std::string fileName = folderName + "/" + std::to_string(i) + ".rbt";
      IntelliTensorOP::tensorFromFile(&ru[i], fileName);
    }
    return ru;
  }
};
}
#endif //IntelliStream_SRC_UTILS_UTILITYFUNCTIONS_HPP_
