//
// Created by haolan on 8/7/23.
//

#include <Streaming/Streamer.h>
#include <Utils/UtilityFunctions.h>
#include "Utils/ConfigMap.hpp"
#include "Utils/ThreadPerf.hpp"
#include <Streaming/SingleThreadStreamer.h>
#include <Streaming/BlockPartitionStreamer.h>

using namespace INTELLI;

torch::Tensor LibAMM::Streamer::run(INTELLI::ConfigMapPtr cfg, torch::Tensor A, torch::Tensor B, uint64_t sketchSize, string metricsPrefix) {
    metrics = newConfigMap(); // has error and pef events: time, instructions, memory access etc.
    matC = newTensor(torch::zeros({A.size(0), B.size(1)}));
    uint64_t isStreaming = cfg->tryU64("isStreaming", 0, true);
    uint64_t threads = cfg->tryU64("threads", 1, true);
    sketchSize = cfg->tryU64("sketchDimension", sketchSize, true);

    if (isStreaming) {
        uint64_t streamingTwoMatrices = cfg->tryU64("streamingTwoMatrices", 0, true);
        if (threads>1) {
            INTELLI_INFO("streaming, multithread "+to_string(threads));
            LibAMM::BlockPartitionStreamer ss;
            ss.setConfig(cfg);
            if (streamingTwoMatrices) {
                *matC = ss.streamingAmm2S(A, B, sketchSize);
            } else *matC = ss.streamingAmm(A, B, sketchSize);
            metrics = ss.getMetrics();
            metrics->addPrefixToKeys(metricsPrefix);
        } else {
            INTELLI_INFO("streaming, singlethread");
            INTELLI_INFO(cfg->toString());
            LibAMM::SingleThreadStreamer ss;
            ss.setConfig(cfg);
            ss.prepareRun(A, B);
            if (streamingTwoMatrices) {
                *matC = ss.streamingAmm2S(A, B, sketchSize);
            } else {
                *matC = ss.streamingAmm(A, B, sketchSize);
            }
            metrics = ss.getMetrics();
            metrics->addPrefixToKeys(metricsPrefix);
        }
    }
    else{
        // non-streaming
        cfg->edit(metricsPrefix+"useCPP", (uint64_t)1);
        uint64_t forceMP = cfg->tryU64("forceMP", 0, true);
        // uint64_t elapsedTime = 0;

        if (threads > 1 || forceMP) {
            INTELLI_INFO("AMM non-streaming, multithread "+to_string(threads));
            LibAMM::BlockPartitionRunner br;
            br.setConfig(cfg);
            *matC = br.runAMM(A, B);
            metrics = br.getMetrics();
            metrics->addPrefixToKeys(metricsPrefix);
            // metrics example, metricsPrefix="AMM"
            // key       value   type
            // AMMPerfElapsedTime      3125    U64
            // AMMThread0CacheMiss     20605   U64
            // AMMThread0CacheRefs     109254  U64
            // AMMThread0CpuClock      2126446 U64
            // AMMThread0CpuCycle      5279889 U64
            // AMMThread0Instructions  4868176 U64
            // AMMThread0PerfElapsedTime       2129    U64
            // AMMThread0TaskClock     2128291 U64
            // AMMThread1CacheMiss     15074   U64
            // AMMThread1CacheRefs     96926   U64
            // AMMThread1CpuClock      3096037 U64
            // ...
        } else {
            INTELLI_INFO("AMM non-streaming, singlethread");
            uint64_t coreBind = cfg->tryU64("coreBind", 0, true);
            UtilityFunctions::bind2Core((int) coreBind);
            LibAMM::CPPAlgoTable cppAlgoTable;
            std::string cppAlgoTag = cfg->tryString("cppAlgoTag", "mm", true);
            LibAMM::AbstractCPPAlgoPtr cppAlgoPtr = cppAlgoTable.findCppAlgo(cppAlgoTag);
            cppAlgoPtr->setConfig(cfg);
            ThreadPerf pef(-1);
            pef.setPerfList();
            pef.start();
            *matC = cppAlgoPtr->amm(A, B, sketchSize);
            pef.end();
            metrics = pef.resultToConfigMap();
            metrics->addPrefixToKeys(metricsPrefix);
            // metrics example, metricsPrefix="AMM"
            // AMMCacheMiss,8596,U64
            // AMMCacheRefs,76066,U64
            // AMMCpuClock,2615984,U64
            // AMMCpuCycle,6501701,U64
            // AMMInstructions,3269080,U64
            // AMMPerfElapsedTime,2624,U64
            // AMMTaskClock,2618774,U64
            // AMMFroError,0.119820,Double
            double throughput = (A.size(0) * 1e6) / metrics->getU64(metricsPrefix+"PerfElapsedTime");
            metrics->edit(metricsPrefix+"Throughput", throughput);
            metrics->edit(metricsPrefix+"ThroughputByElements", (double) (throughput * A.size(1)));
        }

    }

    // calculate error
    torch::Tensor realC = torch::matmul(A, B);
    double froError = INTELLI::UtilityFunctions::relativeFrobeniusNorm(realC, *matC);
    metrics->edit(metricsPrefix+"FroError", (double) froError);
    return *matC;
}
