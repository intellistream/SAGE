//
// Created by haolan on 27/6/23.
//

#include <Streaming/BlockPartitionStreamer.h>
#include <Utils/UtilityFunctions.h>
#include <Parallelization/BlockPartitionRunner.h>
#include <Utils/BS_thread_pool.hpp>
#include <Utils/UtilityFunctions.h>

bool LibAMM::BlockPartitionStreamer::setConfig(INTELLI::ConfigMapPtr cfg) {
  cfgGlobal = cfg;
  /**
  * @brief 1.set the algo
  */
  std::string cppAlgoTag = cfg->tryString("cppAlgoTag", "mm", true);
  cppAlgoPtr = cppAlgoTable.findCppAlgo(cppAlgoTag);
  cppAlgoPtr->setConfig(cfg);
  /**
   * @brief 2. set the batch size
   */
  batchSize = cfg->tryU64("batchSize", 1, true);
  threads = cfg->tryU64("threads", 1, true);
  coreBind = cfg->tryU64("coreBind", 0, true);
  return true;
}

torch::Tensor LibAMM::BlockPartitionStreamer::streamingAmm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize) {
  assert(sketchSize);
  uint64_t aRows = A.size(0);
  cfgGlobal->edit("streamingTupleCnt", (uint64_t) aRows);
  if (batchSize > aRows) {
    batchSize = aRows;
  }
  LibAMM::TimeStamper tsGen;
  tsGen.setConfig(cfgGlobal);
  myTs = tsGen.getTimeStamps();
  INTELLI_INFO("Generate time stamp done");
  matC = newTensor(torch::zeros({A.size(0), B.size(1)}));
  INTELLI_INFO("Start Streaming A rows");
  uint64_t startRow = 0;
  uint64_t endRow = startRow + batchSize;
  uint64_t tNow = 0;
  uint64_t tEXpectedArrival = myTs[endRow - 1]->arrivalTime;
  uint64_t tp = 0;
  uint64_t tDone = 0;
  size_t slice_size = batchSize / threads;

  // pre-partition
  std::vector<std::vector<torch::Tensor>> partitions;
  uint64_t start = 0;
  uint64_t end = batchSize;
  for (int i = 0; i < std::ceil(aRows / batchSize); ++i) {
    //partitions.push_back(vector<torch::Tensor>(threads));
    partitions.emplace_back(threads);
    for (uint64_t j = 0; j < threads; ++j) {
      size_t startRowThread = start + j * slice_size;
      size_t endRowThread = (j == threads - 1) ? end : startRowThread + slice_size;
      partitions[i][j] = A.slice(0, startRowThread, endRowThread);
    }
    start += batchSize;
    end += batchSize;
    if (end > aRows) end = aRows;
  }
  auto pool = std::make_shared<BS::thread_pool>(threads);
  BS::multi_future<void> tasks(threads);
  int index = -1;

  auto tstart = std::chrono::high_resolution_clock::now();
  while (startRow < aRows) {
    index++;
    tNow = chronoElapsedTime(tstart);
    while (tNow < tEXpectedArrival) {
      tNow = chronoElapsedTime(tstart);
    }
    for (size_t i = 0; i < threads; ++i) {
      tasks[i] = pool->submit([&, i]() {
        INTELLI::UtilityFunctions::bind2Core(i + coreBind);
        size_t startRowThread = startRow + i * slice_size;
        size_t endRowThread = (i == threads - 1) ? endRow : startRowThread + slice_size;
        matC->slice(0, startRowThread, endRowThread) = cppAlgoPtr->amm(partitions[index][i], B, sketchSize);
      });
    }
    tasks.wait();
    tp = chronoElapsedTime(tstart);
    for (size_t i = startRow; i < endRow; i++) {
      myTs[i]->processedTime = tp;
    }
    /**
     * @brief update the indexes
     */
    startRow += batchSize;
    endRow += batchSize;
    if (endRow >= aRows) {
      endRow = aRows;
    }
    tEXpectedArrival = myTs[endRow - 1]->arrivalTime;
  }
  tDone = chronoElapsedTime(tstart);
  INTELLI_INFO("Done in " + to_string(tDone) + "us");
  throughput = aRows * 1e6 / tDone;
  double throughputByElements = throughput * A.size(1);
  double latency95 = getLatencyPercentage(0.95);
  metrics->edit("throughput", throughput);
  metrics->edit("throughputByElements", throughputByElements);
  metrics->edit("95%latency", latency95);
  return *matC;
}

torch::Tensor LibAMM::BlockPartitionStreamer::streamingAmm2S(torch::Tensor A, torch::Tensor B, uint64_t sketchSize) {
  assert(sketchSize);
  uint64_t aRows = A.size(0);
  cfgGlobal->edit("streamingTupleCnt", (uint64_t) aRows);
  if (batchSize > aRows) {
    batchSize = aRows;
  }
  LibAMM::TimeStamper tsGen, tsGenB;
  tsGen.setConfig(cfgGlobal);
  myTs = tsGen.getTimeStamps();

  tsGenB.setSeed(7758258);
  tsGenB.setConfig(cfgGlobal);
  myTsB = tsGenB.getTimeStamps();
  INTELLI_INFO("Generate time stamps for two streams done");
  matC = newTensor(torch::zeros({A.size(0), B.size(1)}));
  //INTELLI_INFO("I am mm");
  INTELLI_INFO("Start Streaming A rows and B cols");
  uint64_t startRow = 0;
  uint64_t endRow = startRow + batchSize;
  uint64_t tNow = 0;
  uint64_t tEXpectedArrival = myTs[endRow - 1]->arrivalTime;
  if (myTsB[endRow - 1]->arrivalTime > tEXpectedArrival) {
    tEXpectedArrival = myTsB[endRow - 1]->arrivalTime;
  }
  uint64_t tDone = 0;
  uint64_t iterationCnt = 0;
  torch::Tensor incomingA, incomingB, newArrivedB, oldArrivedA;
  uint64_t aBCols = 0, lastABCols = 0;

  size_t slice_size = batchSize / threads;
  auto pool = std::make_shared<BS::thread_pool>(threads);
  BS::multi_future<void> tasks(threads);

  auto tstart = std::chrono::high_resolution_clock::now();

  while (startRow < aRows) {
    tNow = chronoElapsedTime(tstart);
    incomingB = B.slice(1, startRow, endRow);
    newArrivedB = B.slice(1, 0, endRow);
    while (tNow < tEXpectedArrival) {
      tNow = chronoElapsedTime(tstart);
      //usleep(1);
    }
    INTELLI_INFO("batch of " + to_string(startRow) + " to " + to_string(endRow) + " are ready");
    /**
     * @brief now, the whole batch has arrived, compute
     */
    /**
     * @brief do the incomingA*newArrivedB part
     */
    vector<torch::Tensor> aBs(threads);
    for (size_t i = 0; i < threads; ++i) {
      tasks[i] = pool->submit([&, i]() {
        INTELLI::UtilityFunctions::bind2Core(i + coreBind);
        size_t startRowThread = startRow + i * slice_size;
        size_t endRowThread = (i == threads - 1) ? endRow : startRowThread + slice_size;
        auto subA = A.slice(0, startRowThread, endRowThread);

        aBs[i] = cppAlgoPtr->amm(subA, newArrivedB, sketchSize);
      });
    }
    tasks.wait();
    torch::Tensor aB = torch::cat(aBs, 0);

    lastABCols = aBCols;
    aBCols = aB.size(1);
    matC->slice(0, startRow, endRow).slice(1, 0, aBCols).copy_(aB);
    /**
    * @brief do the oldArrivedA*incomingB part
    */
    if (iterationCnt != 0) {
      torch::Tensor aB2 = torch::empty({(long) oldArrivedA.size(0), incomingB.size(1)});
      std::vector<std::future<void>> tasks(threads);

      for (size_t i = 0; i < threads; ++i) {
        tasks[i] = pool->submit([&, i]() { // Capture by reference, but capture 'i' by value
          INTELLI::UtilityFunctions::bind2Core(i + 1);
          size_t slice_size = oldArrivedA.size(0) / threads;
          size_t startRowThread = i * slice_size;
          size_t endRowThread = (i == threads - 1) ? oldArrivedA.size(0) : startRowThread + slice_size;

          auto oldArrivedA_sub = oldArrivedA.slice(0, startRowThread, endRowThread);
          auto subAB2 = cppAlgoPtr->amm(oldArrivedA_sub, incomingB, sketchSize);
          aB2.slice(0, startRowThread, endRowThread) = subAB2;
        });
      }
      for (auto &task : tasks) {
        task.get();  // wait for tasks to finish
      }
      //aB2=cppAlgoPtr->amm(oldArrivedA, incomingB, sketchSize);

      uint64_t aB2Rows = aB2.size(0);
      uint64_t aB2Cols = aB2.size(1);
      matC->slice(0, 0, aB2Rows).slice(1, lastABCols, lastABCols + aB2Cols).copy_(aB2);
    }
    oldArrivedA = A.slice(0, 0, endRow);
    /**
     * @brief update the indexes
     */
    startRow += batchSize;
    endRow += batchSize;
    if (endRow >= aRows) {
      endRow = aRows;
    }
    tEXpectedArrival = myTs[endRow - 1]->arrivalTime;
    if (myTsB[endRow - 1]->arrivalTime > tEXpectedArrival) {
      tEXpectedArrival = myTsB[endRow - 1]->arrivalTime;
    }
    iterationCnt++;
  }
  tDone = chronoElapsedTime(tstart);
  /**
   * @brief The latency calculation is different from one stream case here,
   * as older A will still be probed by newer B
   */
  for (size_t i = 0; i < aRows; i++) {
    myTs[i]->processedTime = tDone;
  }
  INTELLI_INFO("Done in " + to_string(tDone) + "us");
  throughput = aRows * 1e6 / tDone;
  double throughputByElements = throughput * A.size(1);
  double latency95 = getLatencyPercentage(0.95);
  metrics->edit("throughput", throughput);
  metrics->edit("throughputByElements", throughputByElements);
  metrics->edit("95%latency", latency95);
  return *matC;
}
double LibAMM::BlockPartitionStreamer::getLatencyPercentage(double fraction) {
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
