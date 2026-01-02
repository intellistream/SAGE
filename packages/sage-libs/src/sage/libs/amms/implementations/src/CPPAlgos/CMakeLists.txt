add_sources(
        AbstractCPPAlgo.cpp
        CRSCPPAlgo.cpp
        WeightedCRCPPAlgo.cpp
        CPPAlgoTable.cpp
        CRSV2CPPAlgo.cpp
        BCRSCPPAlgo.cpp
        EWSCPPAlgo.cpp
        CoOccurringFDCPPAlgo.cpp
        BetaCoOFDCPPAlgo.cpp
        CountSketchCPPAlgo.cpp
        INT8CPPAlgo.cpp
        TugOfWarCPPAlgo.cpp
        SMPPCACPPAlgo.cpp

        FastJLTCPPAlgo.cpp
        RIPCPPAlgo.cpp
        BlockLRACPPAlgo.cpp
        ProductQuantizationRaw.cpp
        ProductQuantizationHash.cpp
        VectorQuantization.cpp
)
if (DEFINED ENV{LibAMM_CL})
    add_sources(
            CLMMCPPAlgo.cpp
    )
endif ()
