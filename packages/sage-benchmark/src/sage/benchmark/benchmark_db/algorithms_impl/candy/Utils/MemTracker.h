//
// Created by tony on 27/12/23.
//

#ifndef FAISS_TUTORIAL_CPP_MEMTRACKER_H_
#define FAISS_TUTORIAL_CPP_MEMTRACKER_H_
#include <iostream>
#include <iomanip>
#include <fstream>
#include <string>
#include <csignal>
#include <sys/time.h>
#include <vector>
#include <thread>
namespace INTELLI {

/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @class  MemoryTracker Utils/MemoryTracker.hpp
 * @brief The top entity to trace current, average and maximum memory foot print
 * @note The default unit is KB, will use Linux timer to keep sampling memory usage
 * @note  usage
 * - create a class
 * - call INTELLI::MemoryTracker::setActiveInstance(&xxx) to register this to linux timer
 * - call @ref start to start the sampling
 * - call @ref end to end the sampling
 * - call @ref getAvgMem, @ref getMaxMem, or @ref getCurMem to get the result, @ref getCurMem is a instant function rather than reporting the sampled results
 * @warning Never use multiple instance of INTELLI::MemoryTracker::setActiveInstance(&xxx)
 */
class MemoryTracker;
class MemoryTracker {
 public:
  MemoryTracker() {

  }
  /**
* @brief To start memory usage tracing
* @param sec the second of sampling
* @param usec the micro-second of sampling
* @note call after @ref setPerfList
*/
  void start(uint64_t sec, uint64_t usec = 0) {
    struct itimerval itv;
    itv.it_interval.tv_sec = sec;
    itv.it_interval.tv_usec = usec;
    itv.it_value = itv.it_interval;
    maxMem = 0;
    avgMem = 0;
    sampleCnt = 0;
    sumMem = 0;
    isRunning = true;
    maxCpuUti = 0;
    sumCpuUti = 0;
    cpuSampleCnt = 0;
    reportMemoryUsage();
    reportCpuUti();
    cores = std::thread::hardware_concurrency();
    totalTimeOld = std::vector<uint64_t>(cores);
    totalIdleOld = std::vector<uint64_t>(cores);
    setitimer(ITIMER_REAL, &itv, NULL);

    // Set up the signal handler for SIGALRM
    signal(SIGALRM, sigHandler);

  }

  static void setActiveInstance(MemoryTracker *ins);
  ~MemoryTracker() {
    //  std::cout << "MemoryTracker destroyed." << std::endl;
    // Disable the timer
    if (isRunning) {
      stop();
    }
    // stop();
  }

  void triggerMemorySample() {
    reportMemoryUsage();
    reportCpuUti();
  }

  /**
* @brief To end memory usage tracing
*/
  void stop() {
    struct itimerval itv = {};
    setitimer(ITIMER_REAL, &itv, NULL);
    isRunning = false;
    reportCpuUti();
  }
  /**
* @brief To return the average memory usage during the sampling
* @return size_t the memory usage in KB
*/
  size_t getAvgMem() {
    return sumMem / sampleCnt;
  }
  /**
* @brief To return the average Cpu  utilization rate during the sampling
* @return the fractional
*/
  double getAvgCpu() {
    return sumCpuUti / cpuSampleCnt;
  }
  /**
* @brief To return the max memory usage during the sampling
* @return size_t the memory usage in KB
*/
  size_t getMaxMem() {
    return maxMem;
  }
  /**
* @brief To return the max Cpu  utilization rate during the sampling
* @return the fractional
*/
  double getMaxCpu() {
    return maxCpuUti;
  }
  /**
 * @brief To return the current memory usage when calling this function
 * @return size_t the memory usage in KB
 */
  size_t getCurMem() {
    return getCurrentMemoryUsage();
  }
 private:
  size_t maxMem, avgMem, sumMem;
  size_t sampleCnt = 0, cpuSampleCnt = 0;
  std::vector<uint64_t> totalTimeOld;
  std::vector<uint64_t> totalIdleOld;
  double sumCpuUti = 0, maxCpuUti = 0;
  size_t cores = 0;
  bool isRunning = false;
  static void sigHandler(int signo);

  void reportMemoryUsage() {
    // Get current memory usage (in bytes)
    size_t currentMemoryUsage = getCurrentMemoryUsage();
    sumMem += currentMemoryUsage;
    if (currentMemoryUsage > maxMem) {
      maxMem = currentMemoryUsage;
    }
    sampleCnt++;
    // Display memory usage
    // std::cout << "Memory Usage: " << formatMemorySize(currentMemoryUsage) << std::endl;
  }
  void reportCpuUti() {
    double curCpu = getCpuUtilization();
    if (curCpu >= 0) {
      cpuSampleCnt++;
      if (curCpu > maxCpuUti) {
        maxCpuUti = curCpu;
      }
      sumCpuUti += curCpu;
      //std::cout<<curCpu<<std::endl;
    }

  }

  size_t getCurrentMemoryUsage() {
    // Read the VmRSS field from /proc/self/status
    std::ifstream statusFile("/proc/self/status");
    std::string line;

    while (std::getline(statusFile, line)) {
      if (line.compare(0, 6, "VmRSS:") == 0) {
        size_t memoryUsageKB = std::stoul(line.substr(7));
        return memoryUsageKB;
      }
    }

    return 0; // Return 0 if VmRSS is not found (error handling)
  }

  double get_core_utilization(int core_number) {
    // Open /proc/stat file
    std::ifstream stat_file("/proc/stat");
    if (!stat_file.is_open()) {
      std::cerr << "Error opening /proc/stat" << std::endl;
      return -1.0;
    }

    // Read the lines until finding the line related to the specified core
    std::string line;
    std::string core_label = "cpu" + std::to_string(core_number);
    while (std::getline(stat_file, line)) {
      if (line.compare(0, core_label.size(), core_label) == 0) {
        break;
      }
    }

    // Close the file
    stat_file.close();

    // Parse the CPU utilization values for the specified core
    std::istringstream iss(line);
    std::string cpuLabel;
    long user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice;
    iss >> cpuLabel >> user >> nice >> system >> idle >> iowait >> irq >> softirq >> steal >> guest >> guest_nice;

    // Calculate total CPU time for the specified core
    long totalCpuTime = user + nice + system + idle + iowait + irq + softirq + steal + guest + guest_nice;

    // Calculate the CPU utilization percentage for the specified core
    double cpuUtilization = 100.0
        * (1.0 - static_cast<double>(idle - totalIdleOld[core_number]) / (totalCpuTime - totalTimeOld[core_number]));
    totalIdleOld[core_number] = idle;
    totalTimeOld[core_number] = totalCpuTime;
    if (cpuUtilization >= 100.0) {
      cpuUtilization = 100.0;
    }
    return cpuUtilization;
  }
  double getCpuUtilization() {
    double uti = 0;
    for (size_t i = 0; i < cores; i++) {
      uti += get_core_utilization(i);
    }
    return uti;
    // return usagePercentage;
  }
  std::string formatMemorySize(size_t bytes) {
    const char *suffixes[] = {"B", "KB", "MB", "GB", "TB"};
    int suffixIndex = 0;
    double size = static_cast<double>(bytes);

    while (size >= 1024 && suffixIndex < 4) {
      size /= 1024;
      ++suffixIndex;
    }

    std::stringstream ss;
    ss << std::fixed << std::setprecision(2) << size << " " << suffixes[suffixIndex];
    return ss.str();
  }
};

} // namespace INTELLI

#endif // FAISS_TUTORIAL_CPP_MEMTRACER_H_
