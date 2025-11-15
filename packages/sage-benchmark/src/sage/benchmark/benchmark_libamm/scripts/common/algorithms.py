import pandas as pd


class Algorithm:
    def __init__(self, name, config, resultPath):
        self.name = name
        self.config = pd.DataFrame(config, columns=["key", "value", "type"]).set_index("key")
        self.resultPath = resultPath


################################ CPP ################################
def cpp_algo_config(tag):
    return [
        ["useCPP", 1, "U64"],
        ["cppAlgoTag", tag, "String"],
    ]


MM_CPP = Algorithm("MM", cpp_algo_config("mm"), "mm")

CRS_CPP = Algorithm("CRS", cpp_algo_config("crs"), "crs")
CRSV2_CPP = Algorithm("CRSV2", cpp_algo_config("crsv2"), "crsv2")
BCRS_CPP = Algorithm("BCRS", cpp_algo_config("bcrs"), "bcrs")
WEIGHTED_CRS_CPP = Algorithm("WCRS", cpp_algo_config("weighted-cr"), "wcrs")
EWS_CPP = Algorithm("EWS", cpp_algo_config("ews"), "ews")
FAST_JLT_CPP = Algorithm("FastJLT", cpp_algo_config("fastjlt"), "fastjlt")
RIP_CPP = Algorithm("RIP", cpp_algo_config("rip"), "rip")

COUNT_SKETCH_CPP = Algorithm("CS", cpp_algo_config("countSketch"), "cs")
TUG_OF_WAR_CPP = Algorithm("TOW", cpp_algo_config("tugOfWar"), "tow")
COOFD_CPP = Algorithm("CoFD", cpp_algo_config("cooFD"), "coofd")
BCOOFD_CPP = Algorithm("BCoFD", cpp_algo_config("bcooFD"), "bcoofd")
SMP_PCA_CPP = Algorithm("SMP-PCA", cpp_algo_config("smp-pca"), "smp-pca")

BLOCK_LRA_CPP = Algorithm("BlockLRA", cpp_algo_config("blockLRA"), "blocklra")

INT8_CPP = Algorithm("INT8", cpp_algo_config("int8"), "int8")
PQ_RAW_CPP = Algorithm("PQ-raw", cpp_algo_config("pq-raw"), "pq-raw")
PQ_HASH_CPP = Algorithm("PQ-hash", cpp_algo_config("pq-hash"), "pq-hash")
VQ_CPP = Algorithm("VQ", cpp_algo_config("vq"), "vq")

TRADITIONAL_ALGOS_CPP = [
    CRS_CPP,
    CRSV2_CPP,
    BCRS_CPP,
    WEIGHTED_CRS_CPP,
    EWS_CPP,
    FAST_JLT_CPP,
    RIP_CPP,
]
SKETCHING_ALGOS_CPP = [COUNT_SKETCH_CPP, TUG_OF_WAR_CPP, COOFD_CPP, BCOOFD_CPP, SMP_PCA_CPP]
DECOMPOSITION_ALGOS_CPP = [BLOCK_LRA_CPP]
QUANTIZATION_ALGOS_CPP = [INT8_CPP, PQ_RAW_CPP, PQ_HASH_CPP, VQ_CPP]
#####################################################################


################################# PY ################################
def py_algo_config(tag):
    return [
        ["useCPP", 0, "U64"],
        ["ptFile", f"torchscripts/{tag}.pt", "String"],
    ]


MM_PY = Algorithm("MM", py_algo_config("RAWMM"), "mm-py")

CRS_PY = Algorithm("CRS", py_algo_config("CRS"), "crs-py")
CRSV2_PY = Algorithm("CRSV2", py_algo_config("CRSV2"), "crsv2-py")
BCRS_PY = Algorithm("BCRS", py_algo_config("BernoulliCRS"), "bcrs-py")
WEIGHTED_CRS_PY = Algorithm("WCRS", py_algo_config("WeightedCR"), "wcrs-py")
EWS_PY = Algorithm("EWS", py_algo_config("EWS"), "ews-py")
FAST_JLT_PY = Algorithm("FastJLT", py_algo_config("FastJLT"), "fastjlt-py")
SRHT_PY = Algorithm("SRHT", py_algo_config("SRHT"), "srht-py")

COUNT_SKETCH_PY = Algorithm("CS", py_algo_config("CountSketch"), "cs-py")
TUG_OF_WAR_PY = Algorithm("TOW", py_algo_config("TugOfWar"), "tow-py")
COOFD_PY = Algorithm("CoFD", py_algo_config("CoOccurringFD"), "coofd-py")
BCOOFD_PY = Algorithm("BCoFD", py_algo_config("BetaCoOccurringFD"), "bcoofd-py")


TRADITIONAL_ALGOS_PY = [CRS_PY, CRSV2_PY, BCRS_PY, WEIGHTED_CRS_PY, EWS_PY, FAST_JLT_PY, SRHT_PY]
SKETCHING_ALGOS_PY = [COUNT_SKETCH_PY, TUG_OF_WAR_PY, COOFD_PY, BCOOFD_PY]
DECOMPOSITION_ALGOS_PY = []
QUANTIZATION_ALGOS_PY = []
#####################################################################
