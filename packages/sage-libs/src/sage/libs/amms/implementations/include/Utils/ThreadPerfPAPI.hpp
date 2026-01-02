/*! \file ThreadPerfPAPI.hpp*/
//
// Created by tony on 06/12/22.
//

#ifndef INTELLISTREAM_INCLUDE_UTILS_ThreadPerfPAPIPAPI_H_
#define INTELLISTREAM_INCLUDE_UTILS_ThreadPerfPAPIPAPI_H_
#pragma once

#include <papi.h>
#include <Utils/ConfigMap.hpp>
#include <Utils/ThreadPerf.hpp>

namespace INTELLI {

/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @class ThreadPerfPAPI  Utils/ThreadPerfPAPI.hpp
 * @brief The top entity to provide perf traces by using PAPI lib
 * @note You may overwrite the setPerfList function for your own interested events
 * @warning only works in Linux, and make sure you have opened perf in your kernel and have the access
 * @note Requires the @ref ConfigMap Util
 * @note require configs of perf
 * - perfInstructions, whether or not profile instructions, 1
 * - perfCycles, to record cpu cycles, 0
 * - perfMemRead, to record the memory read times, 0
 * - perfMemWrite, to record the memory write times, 0
 * @note General set up
 * - create the class
 * - call @ref initEventsByCfg, You may overwrite it function in child classes for your own interested events
 * - call @ref start
 * - run your own process
 * - call @ref end
 * - get the results, by @ref getResultById, @ref getResultByName, or @ref  resultToConfigMap
 */
class ThreadPerfPAPI : public ThreadPerf {
 protected:

#define ERROR_RETURN(retval) { fprintf(stderr, "Error %d %s:line %d: \n", retval,__FILE__,__LINE__);   }
  std::vector<std::string> papiStrVec;
  std::vector<uint64_t> papiValueVec;
  std::vector<int> papiEventVec;
  void initPapiLib() {
    retval = PAPI_library_init(PAPI_VER_CURRENT);
    if (retval != PAPI_VER_CURRENT) {
      ERROR_RETURN(retval);
    }

    /* Create the Event Set */
    if ((retval = PAPI_create_eventset(&EventSet)) != PAPI_OK) {
      ERROR_RETURN(retval);
    }
  }
  void clearPapiLib() {
    if ((retval = PAPI_cleanup_eventset(EventSet)) != PAPI_OK) {ERROR_RETURN(retval); }

    if ((retval = PAPI_destroy_eventset(&EventSet)) != PAPI_OK) {ERROR_RETURN(retval); }
  }
  void addPapiEventInline(int ecode) {
    const PAPI_exe_info_t *prginfo = NULL;

    if ((prginfo = PAPI_get_executable_info()) == NULL) {
      fprintf(stderr, "Error in get executable information \n");
      // exit(1);
    }

    size_t start = (size_t) prginfo->address_info.text_start;
    size_t end = (size_t) prginfo->address_info.text_end;

    size_t length = (end - start);
    std::vector<unsigned int> profbuf((size_t) length);
    /* enable the collection of profiling information */
    if ((retval = PAPI_profil(profbuf.data(), length, (vptr_t) start, 65536, EventSet,
                              ecode, 100000, PAPI_PROFIL_POSIX | PAPI_PROFIL_BUCKET_16)) != PAPI_OK) {
      // ERROR_RETURN(ecode);
    }
    if ((retval = PAPI_add_event(EventSet, ecode)) != PAPI_OK) {
      fprintf(stderr,
              "PAPI event code error adding %d: %s\n",
              retval,
              PAPI_strerror(retval));
    }
  }

  int retval, EventSet = PAPI_NULL, dummycollect = 0, eventcode;
 public:

  ThreadPerfPAPI() {}

  /**
   * @brief To setup this perf to specific cpu
   * @param cpu >=0 for any specific cpu, =-1 for all cpu that may run this process
   */
  ThreadPerfPAPI(int cpu) {
    std::cout << cpu << endl;
    initPapiLib();
    //setPerfList();
  }
  /**
   * @brief to add a paipi event to be detected
   * @param displayTag the tag to be displayed in your results
   * @param code the papi lib event code
  */
  void addPapiTag(std::string displayTag, int code) {
    papiStrVec.push_back(displayTag);
    papiValueVec.push_back(0);
    papiEventVec.push_back(code);
    //555
  }
  /**
  * @brief to add a paipi event to be detected
  * @param displayTag the tag to be displayed in your results
  * @param papiTag the built-in tag of papi lib
 */
  void addPapiTag(std::string displayTag, std::string papiTag) {
    int ecode = 0;
    if ((retval = PAPI_event_name_to_code(papiTag.data(), &ecode)) != PAPI_OK) {
      fprintf(stderr, "PAPI event code error %d: %s\n", retval, PAPI_strerror(retval));
      //  exit(-1);
      return;
    }
    papiStrVec.push_back(displayTag);
    papiValueVec.push_back(0);
    papiEventVec.push_back(ecode);
  }
  /**
     * @brief To set up all your interest perf events
     */
  virtual void setPerfList() {
    /*addPapiTag("instructions",PAPI_TOT_INS);

    addPapiTag("cycles",PAPI_TOT_CYC );

    addPapiTag("memRead", PAPI_LD_INS);
    addPapiTag("memWrite", PAPI_SR_INS);
  */
    //pairs.push_back(PerfPair(COUNT_HW_CACHE_L1I_LOADS_MISSES, "L1ILoadMiss"));
  }

  /**
   * @brief To start perf tracing
   * @note call after @ref setPerfList
   */
  virtual void start() {
    for (size_t i = 0; i < papiStrVec.size(); i++) {
      addPapiEventInline(papiEventVec[i]);
    }
    gettimeofday(&tstart, NULL);
    /* Start counting events in the Event Set */
    if ((retval = PAPI_start(EventSet)) != PAPI_OK) {
      ERROR_RETURN(retval);
    }
  }

  /**
   * @brief To end a perf tracing
   */
  virtual void end() {
    gettimeofday(&tend, NULL);
    auto values = papiValueVec.data();
    if ((retval = PAPI_stop(EventSet, (long long *) values)) != PAPI_OK) {
      fprintf(stderr,
              "PAPI stop error %d: %s\n",
              retval,
              PAPI_strerror(retval));
    }

  }

  /**
   * @brief Get the perf result by its index of @ref PerfPair
   * @param idx The index
   * @return The value
   */
  virtual uint64_t getResultById(size_t idx) {

    return papiValueVec[idx];
  }

  /**
   * @brief Get the perf result by its name of of @ref PerfPair
   * @param idx The index
   * @return The value
   */
  virtual uint64_t getResultByName(string name) {
    for (size_t i = 0; i < papiStrVec.size(); i++) {
      if (papiStrVec[i] == name) {
        return papiValueVec[i];
      }
    }
    return 0;
  }

  /**
   * @brief convert the perf result into a @ref ConfigMap
   * @return The key-value store of configMap, in shared pointer
   * @note must stop after calling stop
   */
  virtual ConfigMapPtr resultToConfigMap() {
    ConfigMapPtr ru = newConfigMap();
    for (size_t i = 0; i < papiStrVec.size(); i++) {
      ru->edit(papiStrVec[i], (uint64_t) papiValueVec[i]);
    }
    //additional test the elapsed time
    ru->edit("perfElapsedTime", (uint64_t) timeLastUs(tstart, tend));
    return ru;
  }
  void initEventsByCfg(ConfigMapPtr cfg) {
    if (cfg->tryU64("perfUseExternalList", 0)) {
      std::string perfListSrc = cfg->tryString("perfListSrc", "perfLists/perfList.csv", 1);
      ConfigMapPtr perfList = newConfigMap();
      perfList->fromFile(perfListSrc);
      auto strMap = perfList->getStrMap();
      for (auto &iter : strMap) {
        addPapiTag(iter.first, iter.second);
        //return;
      }
    }
    /*if (cfg->tryU64("perfInstructions", 0)) {
      addPapiTag("instructions", PAPI_TOT_INS);
    }
    if (cfg->tryU64("perfCycles", 0)) {
      addPapiTag("cpuCycle", PAPI_TOT_CYC);
    }
    if (cfg->tryU64("perfMemRead", 0)) {
      addPapiTag("memRead", PAPI_LD_INS);
    }
    if (cfg->tryU64("perfMemWrite", 0)) {
      addPapiTag("memWrite", PAPI_SR_INS);
    }
    if (cfg->tryU64("perfX64InstructionStall", 0)) {
      addPapiTag("instructionStall", "ILD_STALL:IQ_FULL");
    }*/
    // addPapiTag("llcMiss", ":IQ_FULL");
  }
};

/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @typedef ThreadPerfPAPIPtr
 * @brief The class to describe a shared pointer to @ref ThreadPerfPAPI
 */
typedef std::shared_ptr<INTELLI::ThreadPerfPAPI> ThreadPerfPAPIPtr;
/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @def newThreadPerfPAPI
 * @brief (Macro) To creat a new @ref ThreadPerfPAPI under shared pointer.
 */
#define  newThreadPerfPAPI std::make_shared<INTELLI::ThreadPerfPAPI>
}
#endif //INTELLISTREAM_INCLUDE_UTILS_ThreadPerfPAPI_H_
