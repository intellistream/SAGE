//
// Created by tony on 25/05/23.
//

#include <CPPAlgos/CPPAlgoTable.h>
#include <CPPAlgos/CRSCPPAlgo.h>
#include <CPPAlgos/CRSV2CPPAlgo.h>

#include <CPPAlgos/CountSketchCPPAlgo.h>
#include <CPPAlgos/ProductQuantizationRaw.h>
#include <CPPAlgos/ProductQuantizationHash.h>
#include <CPPAlgos/VectorQuantization.h>
#include <CPPAlgos/BCRSCPPAlgo.h>
#include <CPPAlgos/EWSCPPAlgo.h>
#include <CPPAlgos/CoOccurringFDCPPAlgo.h>
#include <CPPAlgos/BetaCoOFDCPPAlgo.h>
#include <CPPAlgos/WeightedCRCPPAlgo.h>
#include <CPPAlgos/SMPPCACPPAlgo.h>
#include <CPPAlgos/INT8CPPAlgo.h>
#include <CPPAlgos/TugOfWarCPPAlgo.h>

#include <CPPAlgos/FastJLTCPPAlgo.h>
#include <CPPAlgos/BlockLRACPPAlgo.h>
#include <CPPAlgos/RIPCPPAlgo.h>
#include <include/opencl_config.h>
#if LibAMM_CL == 1
#include <CPPAlgos/CLMMCPPAlgo.h>
#endif
namespace LibAMM {
LibAMM::CPPAlgoTable::CPPAlgoTable() {
  algoMap["mm"] = newAbstractCPPAlgo();
  algoMap["crs"] = newCRSCPPAlgo();
  algoMap["crsV2"] = newCRSV2CPPAlgo();
  algoMap["countSketch"] = newCountSketchCPPAlgo();
  algoMap["bcrs"] = newBCRSCPPAlgo();
  algoMap["ews"] = newEWSCPPAlgo();
  algoMap["cooFD"] = newCoOccurringFDCPPAlgo();
  algoMap["bcooFD"] = newBetaCoOFDCPPAlgo();
  algoMap["int8"] = newINT8CPPAlgo();
  algoMap["int8_fp32"] = newINT8CPPAlgo();
  algoMap["int8_fp64"] = newINT8CPPAlgo();
  algoMap["tugOfWar"] = newTugOfWarCPPAlgo();
  algoMap["weighted-cr"] = newWeightedCRCPPAlgo();
  algoMap["smp-pca"] = newSMPPCACPPAlgo();

  algoMap["blockLRA"] = newBlockLRACPPAlgo();
  algoMap["rip"] = newRIPCPPAlgo();
  algoMap["fastjlt"] = newFastJLTCPPAlgo();
  algoMap["pq-raw"] = newProductQuantizationRawAlgo();
  algoMap["pq-hash"] = newProductQuantizationHashAlgo();
  algoMap["vq"] = newVectorQuantizationAlgo();
  algoMap["pq"] = newVectorQuantizationAlgo();
#if LibAMM_CL == 1
  algoMap["cl"] = newCLMMCPPAlgo();
#endif
}
} // LibAMM
