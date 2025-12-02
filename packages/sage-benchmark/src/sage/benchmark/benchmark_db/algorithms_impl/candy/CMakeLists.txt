add_sources(
        CANDYObject.cpp
        AbstractIndex.cpp
        BucketedFlatIndex.cpp
        BufferedCongestionDropIndex.cpp
        FlatIndex.cpp
        #FlatAMMIPIndex.cpp
        #FlatAMMIPObjIndex.cpp
        #ParallelPartitionIndex.cpp
        OnlinePQIndex.cpp
        #OnlineIVFLSHIndex.cpp
        #OnlineIVFL2HIndex.cpp
        IndexTable.cpp
        #PQIndex.cpp
        HNSWNaiveIndex.cpp
        FaissIndex.cpp
        #YinYangGraphIndex.cpp
        #YinYangGraphSimpleIndex.cpp
        CongestionDropIndex.cpp
        NNDescentIndex.cpp
        FlannIndex.cpp
        DPGIndex.cpp
        LSHAPGIndex.cpp
        FlatGPUIndex.cpp
        ConcurrentIndex.cpp
)
add_subdirectory(HashingModels)
add_subdirectory(ParallelPartitionIndex)
#add_subdirectory(PQIndex)
add_subdirectory(OnlinePQIndex)
add_subdirectory(HNSWNaive)
#add_subdirectory(YinYangGraphIndex)
add_subdirectory(CongestionDropIndex)
add_subdirectory(FlannIndex)
add_subdirectory(LSHAPGIndex)
add_subdirectory(FlatGPUIndex)

#if (ENABLE_CUDA)
#    add_subdirectory(SONG)
#endif ()

if (ENABLE_RAY)
    add_subdirectory(DistributedPartitionIndex)
    add_sources(DistributedPartitionIndex.cpp)
endif ()
if (ENABLE_SPTAG)
    add_sources(SPTAGIndex.cpp)
endif ()
