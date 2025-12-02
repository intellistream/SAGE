//
// Created by tony on 25/05/23.
//

#include <BucketedFlatIndex.h>
//#include <BufferedCongestionDropIndex.h>
//#include <CongestionDropIndex.h>
#include <DPGIndex.h>
#include <FaissIndex.h>
// #include <FlannIndex.h>
//#include <FlatAMMIPIndex.h>
//#include <FlatAMMIPObjIndex.h>
#include <FlatIndex.h>
// #include <HNSWNaiveIndex.h>
#include <IndexTable.h>
#include <LSHAPGIndex.h>
#include <NNDescentIndex.h>
//#include <OnlineIVFL2HIndex.h>
//#include <OnlineIVFLSHIndex.h>
#include <OnlinePQIndex.h>
//#include <PQIndex.h>
#include <ParallelPartitionIndex.h>
//#include <YinYangGraphIndex.h>
// #include <FlatGPUIndex.h>
//#include <YinYangGraphSimpleIndex.h>
#include <include/opencl_config.h>
#include <include/ray_config.h>
#include <include/sptag_config.h>
#if CANDY_CL == 1
//#include <CPPAlgos/CLMMCPPAlgo.h>
#endif
#if CANDY_RAY == 1
#include <DistributedPartitionIndex.h>
#endif
#if CANDY_SPTAG == 1
#include <SPTAGIndex.h>
#endif
//#ifdef ENABLE_CUDA
// #include <SONG/SONG.hpp>
//#endif
namespace CANDY {
CANDY::IndexTable::IndexTable() {
  indexMap["null"] = newAbstractIndex();
  indexMap["flat"] = newFlatIndex();
  //indexMap["flatAMMIP"] = newFlatAMMIPIndex();
  //indexMap["flatAMMIPObj"] = newFlatAMMIPObjIndex();
  indexMap["bucketedFlat"] = newBucketedFlatIndex();
  //indexMap["parallelPartition"] = newParallelPartitionIndex();
  indexMap["onlinePQ"] = newOnlinePQIndex();
  //indexMap["onlineIVFLSH"] = newOnlineIVFLSHIndex();
  //indexMap["onlineIVFL2H"] = newOnlineIVFL2HIndex();
  //indexMap["PQ"] = newPQIndex();
  // indexMap["HNSWNaive"] = newHNSWNaiveIndex();
  // indexMap["NSW"] = newNSWIndex();
  indexMap["faiss"] = newFaissIndex();
  //indexMap["yinYang"] = newYinYangGraphIndex();
  //indexMap["yinYangSimple"] = newYinYangGraphSimpleIndex();
  //indexMap["congestionDrop"] = newCongestionDropIndex();
  //indexMap["bufferedCongestionDrop"] = newBufferedCongestionDropIndex();
  indexMap["nnDescent"] = newNNDescentIndex();
  // indexMap["Flann"] = newFlannIndex();
  indexMap["DPG"] = newDPGIndex();
  indexMap["LSHAPG"] = newLSHAPGIndex();
  // indexMap["flatGPU"] = newFlatGPUIndex();
//#ifdef ENABLE_CUDA
  // indexMap["SONG"] = newSONG();
//#endif
#if CANDY_CL == 1
  // indexMap["cl"] = newCLMMCPPAlgo();
#endif
#if CANDY_RAY == 1
  indexMap["distributedPartition"] = newDistributedPartitionIndex();
#endif
#if CANDY_SPTAG == 1
  indexMap["SPTAG"] = newSPTAGIndex();
#endif
}
}  // namespace CANDY
