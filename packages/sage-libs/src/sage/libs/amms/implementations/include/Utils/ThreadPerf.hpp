/*! \file ThreadPerf.hpp*/
//
// Created by tony on 06/12/22.
//

#ifndef INTELLISTREAM_INCLUDE_UTILS_ThreadPerf_H_
#define INTELLISTREAM_INCLUDE_UTILS_ThreadPerf_H_
#pragma once

#include <string>
#include <sys/time.h>
#include <assert.h>
#include <fcntl.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <linux/perf_event.h>
#include <signal.h>
#include <memory.h>
#include <memory>
#include <vector>
#include <Utils/ConfigMap.hpp>

#define PERF_ERROR(n) printf(n)
namespace INTELLI {
/**
 * @enum perfTrace
 * @brief The low level description of perf events, used inside, don't touch me UNLESS you know what you are doing
 */
enum perfTrace {
  /* sw tracepoints */
  COUNT_SW_CPU_CLOCK = 0,
  COUNT_SW_TASK_CLOCK = 1,
  COUNT_SW_CONTEXT_SWITCHES = 2,
  COUNT_SW_CPU_MIGRATIONS = 3,
  COUNT_SW_PAGE_FAULTS = 4,
  COUNT_SW_PAGE_FAULTS_MIN = 5,
  COUNT_SW_PAGE_FAULTS_MAJ = 6,

  /* hw counters */
  COUNT_HW_CPU_CYCLES = 7,
  COUNT_HW_INSTRUCTIONS = 8,
  COUNT_HW_CACHE_REFERENCES = 9,
  COUNT_HW_CACHE_MISSES = 10,
  COUNT_HW_BRANCH_INSTRUCTIONS = 11,
  COUNT_HW_BRANCH_MISSES = 12,
  COUNT_HW_BUS_CYCLES = 13,

  /* cache counters */

  /* L1D - data cache */
  COUNT_HW_CACHE_L1D_LOADS = 14,
  COUNT_HW_CACHE_L1D_LOADS_MISSES = 15,
  COUNT_HW_CACHE_L1D_STORES = 16,
  COUNT_HW_CACHE_L1D_STORES_MISSES = 17,
  COUNT_HW_CACHE_L1D_PREFETCHES = 18,

  /* L1I - instruction cache */
  COUNT_HW_CACHE_L1I_LOADS = 19,
  COUNT_HW_CACHE_L1I_LOADS_MISSES = 20,

  /* LL - last level cache */
  COUNT_HW_CACHE_LL_LOADS = 21,
  COUNT_HW_CACHE_LL_LOADS_MISSES = 22,
  COUNT_HW_CACHE_LL_STORES = 23,
  COUNT_HW_CACHE_LL_STORES_MISSES = 24,

  /* DTLB - data translation lookaside buffer */
  COUNT_HW_CACHE_DTLB_LOADS = 25,
  COUNT_HW_CACHE_DTLB_LOADS_MISSES = 26,
  COUNT_HW_CACHE_DTLB_STORES = 27,
  COUNT_HW_CACHE_DTLB_STORES_MISSES = 28,

  /* ITLB - instructiont translation lookaside buffer */
  COUNT_HW_CACHE_ITLB_LOADS = 29,
  COUNT_HW_CACHE_ITLB_LOADS_MISSES = 30,

  /* BPU - branch prediction unit */
  COUNT_HW_CACHE_BPU_LOADS = 31,
  COUNT_HW_CACHE_BPU_LOADS_MISSES = 32,

  /* Special internally defined "counter" */
  /* this is the _only_ floating point value */
  //LIB_SW_WALL_TIME = 33
};

/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @class ThreadPerf  Utils/ThreadPerf.hpp
 * @brief The top entity to provide perf traces, please use this class only UNLESS you know what you are doing
 * @note You may overwrite the setPerfList function for your own interested events
 * @warning only works in Linux, and make sure you have opened perf in your kernel and have the access
 * @note Requires the @ref ConfigMap Util
 * @note General set up
 * - create the class
 * - call @ref setPerfList or @ref initEventsByCfg, You may overwrite the setPerfList function in child classes for your own interested events
 * - call @ref start
 * - run your own process
 * - call @ref end
 * - get the results, by @ref getResultById, @ref getResultByName, or @ref  resultToConfigMap
 */
class ThreadPerf {
 protected:

  /**
   * @class PerfPair Utils/ThreadPerf.hpp
   * @brief a record pair of perf events
   */
  class PerfPair {
   public:
    int ref;
    std::string name;
    uint64_t record;

    PerfPair(int _ref, std::string _name) {
      ref = _ref;
      name = _name;
      record = 0;
    }

    ~PerfPair() {}
  };

  class PerfTool {
   private:
    /**
 * @class PerfEntry Utils/ThreadPerf.hpp
* @brief The low-level entry record of perf, don't touch me
*/
    class PerfEntry {
     public:
      //struct perf_event_attr attr;
      int fds;
      bool addressable;
      uint64_t prevVale;

      PerfEntry() { addressable = false; }

      ~PerfEntry() {}
    };

    /* data */
    std::vector<PerfEntry> entries;
    pid_t myPid;
    int myCpu;
    uint64_t prevValue;
#define LIBPERF_ARRAY_SIZE(x) (sizeof(x)/sizeof(x[0]))
    /**
     * @struct default_attrs
     * @brief The low-level perf descriptions passed to OS
     */
    struct perf_event_attr default_attrs[32] = {
        {.type = PERF_TYPE_SOFTWARE, .config = PERF_COUNT_SW_CPU_CLOCK}, //1
        {.type = PERF_TYPE_SOFTWARE, .config = PERF_COUNT_SW_TASK_CLOCK}, //2
        {.type = PERF_TYPE_SOFTWARE, .config = PERF_COUNT_SW_CONTEXT_SWITCHES},//3
        {.type = PERF_TYPE_SOFTWARE, .config = PERF_COUNT_SW_CPU_MIGRATIONS},//4
        {.type = PERF_TYPE_SOFTWARE, .config = PERF_COUNT_SW_PAGE_FAULTS},//5
        {.type = PERF_TYPE_SOFTWARE, .config = PERF_COUNT_SW_PAGE_FAULTS_MIN},//6
        {.type = PERF_TYPE_SOFTWARE, .config = PERF_COUNT_SW_PAGE_FAULTS_MAJ},//7
        {.type = PERF_TYPE_HARDWARE, .config = PERF_COUNT_HW_CPU_CYCLES},//8
        {.type = PERF_TYPE_HARDWARE, .config = PERF_COUNT_HW_INSTRUCTIONS},//9
        {.type = PERF_TYPE_HARDWARE, .config = PERF_COUNT_HW_CACHE_REFERENCES},//10
        {.type = PERF_TYPE_HARDWARE, .config = PERF_COUNT_HW_CACHE_MISSES},//11
        {.type = PERF_TYPE_HARDWARE, .config = PERF_COUNT_HW_BRANCH_INSTRUCTIONS},//12
        {.type = PERF_TYPE_HARDWARE, .config = PERF_COUNT_HW_BRANCH_MISSES},//13
        {.type = PERF_TYPE_HARDWARE, .config = PERF_COUNT_HW_BUS_CYCLES},//14
        //15
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_L1D | (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //16
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_L1D | (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //17, no x64
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_L1D |
            (PERF_COUNT_HW_CACHE_OP_WRITE << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //18, no x64, no rk3399
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_L1D |
            (PERF_COUNT_HW_CACHE_OP_WRITE << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //19, no x64
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_L1D |
            (PERF_COUNT_HW_CACHE_OP_PREFETCH << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //20
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_L1I | (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //21, no rk3399
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_L1I | (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //22, no rk3399
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_LL | (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //23, no rk3399
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_LL | (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //24,no rk3399
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_LL | (PERF_COUNT_HW_CACHE_OP_WRITE << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //25
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_LL | (PERF_COUNT_HW_CACHE_OP_WRITE << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //26
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_DTLB |
            (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //27, no rk3399
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_DTLB |
            (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //28
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_DTLB |
            (PERF_COUNT_HW_CACHE_OP_WRITE << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //29,no rk3399
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_DTLB |
            (PERF_COUNT_HW_CACHE_OP_WRITE << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //30
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_ITLB |
            (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        //31
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_ITLB |
            (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))},
        //32
        {.type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_BPU | (PERF_COUNT_HW_CACHE_OP_READ << 8)
            | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16))},
        /* { .type = PERF_TYPE_HW_CACHE, .config = (PERF_COUNT_HW_CACHE_BPU | (PERF_COUNT_HW_CACHE_OP_READ << 8) | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16))}, */
    };

    long
    sys_perf_event_open(struct perf_event_attr *hw_event,
                        pid_t pid, int cpu, int group_fd,
                        unsigned long flags) {
      return syscall(__NR_perf_event_open, hw_event, pid, cpu,
                     group_fd, flags);
    }

   public:
    /**
 * @struct default_attrs
 * @brief The low-level perf events send to OS call, don't touch me
 */

    PerfTool() {

    }

    PerfTool(pid_t pid, int cpu) {
      if (pid == -1) { pid = gettid(); }
      myPid = pid;
      myCpu = cpu;
      int nr_counters = 32;
      for (int i = 0; i < nr_counters; i++) {
        PerfEntry entry;
        default_attrs[i].size = sizeof(struct perf_event_attr);
        entry.fds = sys_perf_event_open(&default_attrs[i], pid, cpu, -1, 0);
        if (entry.fds < 0) {
          entry.addressable = false;
        } else {
          entry.addressable = true;
          ioctl(entry.fds, PERF_EVENT_IOC_DISABLE);
          ioctl(entry.fds, PERF_EVENT_IOC_RESET);
        }
        entries.push_back(entry);
      }
    }

    ~PerfTool() {
      for (size_t i = 0; i < entries.size(); i++) {
        if (entries[i].addressable == true) {
          close(entries[i].fds);
          //printf("close perf %d\r\n",i);
        }
      }
    }

    // reading result from a perf trace on [ch], will return 0 if the channel is invaild
    uint64_t readPerf(size_t ch) {
      if (ch > entries.size()) {
        return 0;
      }
      if (entries[ch].addressable == false) {
        return 0;
      }
      uint64_t value;
      int ru = read(entries[ch].fds, &value, sizeof(uint64_t));
      if (ru < 0) {
        PERF_ERROR("invalid read");
      }
      return value;
    }

    // start the perf trace on [ch]
    int startPerf(size_t ch) {
      ioctl(entries[ch].fds, PERF_EVENT_IOC_ENABLE);
      return 1;
    }

    // st the perf trace on [ch]
    int stopPerf(size_t ch) {
      if (ch > entries.size()) {
        return -1;
      }
      if (entries[ch].addressable == false) {
        return -1;
      }
      ioctl(entries[ch].fds, PERF_EVENT_IOC_DISABLE);
      ioctl(entries[ch].fds, PERF_EVENT_IOC_RESET);
      return 1;
    }

    //check the addressability of [ch]
    bool isValidChannel(size_t ch) {
      if (ch > entries.size()) {
        return false;
      }
      return entries[ch].addressable;
    }
  };

  typedef std::shared_ptr<PerfTool> PerfToolPtr;

  std::string getChValueAsString(size_t idx);

  PerfToolPtr myTool;
  /**
   * @brief To contain all of your interested perf events
   */
  std::vector<PerfPair> pairs;
  struct timeval tstart, tend;
  uint64_t latency;
 public:
  ThreadPerf() {}

  /**
   * @brief To setup this perf to specific cpu
   * @param cpu >=0 for any specific cpu, =-1 for all cpu that may run this process
   */
  ThreadPerf(int cpu) {
    myTool = std::make_shared<PerfTool>(0, cpu);
    //setPerfList();
  }

  /**
   * @brief To set up all your interest perf events
   */
  virtual void setPerfList() {
    pairs.push_back(PerfPair(COUNT_HW_CPU_CYCLES, "cpuCycle"));
    pairs.push_back(PerfPair(COUNT_HW_INSTRUCTIONS, "instructions"));
    pairs.push_back(PerfPair(COUNT_HW_CACHE_REFERENCES, "cacheRefs"));
    pairs.push_back(PerfPair(COUNT_HW_CACHE_MISSES, "cacheMiss"));
    pairs.push_back(PerfPair(COUNT_SW_CPU_CLOCK, "cpuClock"));
    pairs.push_back(PerfPair(COUNT_SW_TASK_CLOCK, "taskClock"));
    //pairs.push_back(PerfPair(COUNT_HW_CACHE_L1I_LOADS_MISSES, "L1ILoadMiss"));
  }

  /**
   * @brief To start perf tracing
   * @note call after @ref setPerfList
   */
  virtual void start() {
    for (size_t i = 0; i < pairs.size(); i++) {
      myTool->startPerf(pairs[i].ref);
    }
    gettimeofday(&tstart, NULL);
  }

  /**
   * @brief To end a perf tracing
   */
  virtual void end() {
    gettimeofday(&tend, NULL);
    for (size_t i = 0; i < pairs.size(); i++) {
      pairs[i].record = myTool->readPerf(pairs[i].ref);
      myTool->stopPerf(pairs[i].ref);
    }
  }

  /**
   * @brief Get the perf result by its index of @ref PerfPair
   * @param idx The index
   * @return The value
   */
  virtual uint64_t getResultById(size_t idx) {
    if (idx > pairs.size()) {
      return 0;
    }
    size_t ch = pairs[idx].ref;
    if (myTool->isValidChannel(ch) == false) {
      return 0;
    }
    return pairs[idx].record;
  }

  /**
   * @brief Get the perf result by its name of of @ref PerfPair
   * @param idx The index
   * @return The value
   */
  virtual uint64_t getResultByName(string name) {
    for (size_t i = 0; i < pairs.size(); i++) {
      if (pairs[i].name == name) {
        return pairs[i].record;
      }
    }
    return 0;
  }

  size_t timeLastUs(struct timeval ts, struct timeval te) {
    int64_t s0, e0, s1, e1;
    s0 = ts.tv_sec;
    s1 = ts.tv_usec;
    e0 = te.tv_sec;
    e1 = te.tv_usec;
    return 1000000 * (e0 - s0) + (e1 - s1);
  }

  /**
   * @brief convert the perf result into a @ref ConfigMap
   * @return The key-value store of configMap, in shared pointer
   * @note must stop after calling stop
   */
  virtual ConfigMapPtr resultToConfigMap() {
    ConfigMapPtr ru = newConfigMap();
    for (size_t i = 0; i < pairs.size(); i++) {
      ru->edit(pairs[i].name, (uint64_t) pairs[i].record);
    }
    //additional test the elapsed time
    ru->edit("perfElapsedTime", (uint64_t) timeLastUs(tstart, tend));
    return ru;
  }
  /**
   * @brief init the perf events according to configmap
   * @param cfg tyhe configmap
   */
  virtual void initEventsByCfg(ConfigMapPtr cfg) {
    assert(cfg);
    setPerfList();
  }
};

/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @typedef ThreadPerfPtr
 * @brief The class to describe a shared pointer to @ref ThreadPerf
 */
typedef std::shared_ptr<INTELLI::ThreadPerf> ThreadPerfPtr;
/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @def newThreadPerf
 * @brief (Macro) To creat a new @ref ThreadPerf under shared pointer.
 */
#define  newThreadPerf std::make_shared<INTELLI::ThreadPerf>

}
#endif //INTELLISTREAM_INCLUDE_UTILS_ThreadPerf_H_
