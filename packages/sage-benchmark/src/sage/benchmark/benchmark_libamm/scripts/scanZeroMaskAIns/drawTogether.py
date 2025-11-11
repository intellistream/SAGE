#!/usr/bin/env python3
import os
import sys

import accuBar as accuBar
import groupBar2 as groupBar2
import groupLine as groupLine
import matplotlib
import numpy as np
from autoParase import *
from matplotlib.font_manager import FontProperties
from OoOCommon import *

OPT_FONT_NAME = "Helvetica"
TICK_FONT_SIZE = 22
LABEL_FONT_SIZE = 22
LEGEND_FONT_SIZE = 22
LABEL_FP = FontProperties(style="normal", size=LABEL_FONT_SIZE)
LEGEND_FP = FontProperties(style="normal", size=LEGEND_FONT_SIZE)
TICK_FP = FontProperties(style="normal", size=TICK_FONT_SIZE)

MARKERS = ["*", "|", "v", "^", "", "h", "<", ">", "+", "d", "<", "|", "", "+", "_"]
# you may want to change the color map for different figures
COLOR_MAP = (
    "#B03A2E",
    "#2874A6",
    "#239B56",
    "#7D3C98",
    "#FFFFFF",
    "#F1C40F",
    "#F5CBA7",
    "#82E0AA",
    "#AEB6BF",
    "#AA4499",
)
# you may want to change the patterns for different figures
PATTERNS = [
    "////",
    "o",
    "",
    "||",
    "-",
    "//",
    "\\",
    "o",
    "O",
    "////",
    ".",
    "|||",
    "o",
    "---",
    "+",
    "\\\\",
    "*",
]
LABEL_WEIGHT = "bold"
LINE_COLORS = COLOR_MAP
LINE_WIDTH = 3.0
MARKER_SIZE = 15.0
MARKER_FREQUENCY = 1000

matplotlib.rcParams["ps.useafm"] = True
matplotlib.rcParams["pdf.use14corefonts"] = True
matplotlib.rcParams["xtick.labelsize"] = TICK_FONT_SIZE
matplotlib.rcParams["ytick.labelsize"] = TICK_FONT_SIZE
matplotlib.rcParams["font.family"] = OPT_FONT_NAME
matplotlib.rcParams["pdf.fonttype"] = 42

dataset_acols_mapping = {
    "AST": 765,
    "BUS": 10595,
    "DWAVE": 512,
    "ECO": 260,
    "QCD": 3072,
    "RDB": 2048,
    "UTM": 1700,
    "ZENIOS": 2873,
}


def runPeriod(exePath, algoTag, resultPath, configTemplate="config.csv", prefixTag="null"):
    # resultFolder="periodTests"
    configFname = "config_period_" + str(prefixTag) + ".csv"
    configTemplate = "config_e2e_static_lazy.csv"
    # clear old files
    os.system("cd " + exePath + "&& sudo rm *.csv")
    os.system("cp perfListEvaluation.csv " + exePath)
    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    editConfig(configTemplate, exePath + "temp1.csv", "nnzA", prefixTag)
    editConfig(exePath + "temp1.csv", exePath + "temp2.csv", "cppAlgoTag", algoTag)

    # int8 or int8_fp32
    if algoTag == "int8_fp32":
        editConfig(exePath + "temp2.csv", exePath + "temp1.csv", "fpMode", "fp32")
    else:
        editConfig(exePath + "temp2.csv", exePath + "temp1.csv", "fpMode", "INT8")

    # load Codeword LookUpTable for vq or pq
    pqvqCodewordLookUpTableDir = f"{exePath}/torchscripts/VQ/CodewordLookUpTable"
    pqvqCodewordLookUpTablePath = "dummy"
    import glob

    if algoTag == "vq":
        pqvqCodewordLookUpTablePath = glob.glob(f"{pqvqCodewordLookUpTableDir}/1000_m1_row*")[0]
    elif algoTag == "pq":
        pqvqCodewordLookUpTablePath = glob.glob(f"{pqvqCodewordLookUpTableDir}/1000_m10_row*")[0]
    editConfig(
        exePath + "temp1.csv",
        exePath + configFname,
        "pqvqCodewordLookUpTablePath",
        pqvqCodewordLookUpTablePath,
    )

    # prepare new file
    # run
    os.system(
        "export OMP_NUM_THREADS=1 &&" + "cd " + exePath + "&& sudo ./benchmark " + configFname
    )
    # copy result
    os.system("sudo rm -rf " + resultPath + "/" + str(prefixTag))
    os.system("sudo mkdir " + resultPath + "/" + str(prefixTag))
    os.system("cd " + exePath + "&& sudo cp *.csv " + resultPath + "/" + str(prefixTag))


def runPeriodVector(exePath, algoTag, resultPath, prefixTag, configTemplate="config.csv", reRun=1):
    for i in range(len(prefixTag)):
        if reRun == 2:
            if checkResultSingle(prefixTag[i], resultPath) == 1:
                print("skip " + prefixTag[i])
            else:
                runPeriod(exePath, algoTag, resultPath, configTemplate, prefixTag[i])
        else:
            runPeriod(exePath, algoTag, resultPath, configTemplate, prefixTag[i])


def readResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/default.csv"
    elapsedTime = readConfig(resultFname, "perfElapsedTime")
    memLoad = readConfig(resultFname, "memLoad")
    memStore = readConfig(resultFname, "memStore")
    instructions = readConfig(resultFname, "instructions")
    fpVector = readConfig(resultFname, "fpVector")
    fpScalar = readConfig(resultFname, "fpScalar")
    branchIns = readConfig(resultFname, "branchIns")
    froErr = readConfig(resultFname, "froError")
    return elapsedTime, memLoad, memStore, instructions, fpVector, fpScalar, branchIns, froErr


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    memLoadVec = []
    memStoreVec = []
    instructionsVec = []
    fpVectorVec = []
    fpScalarVec = []
    branchVec = []
    froErrVec = []
    for i in singleValueVec:
        elapsedTime, memLoad, memStore, instructions, fpVector, fpScalar, branchIns, froErr = (
            readResultSingle(i, resultPath)
        )
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        memLoadVec.append(float(memLoad))
        memStoreVec.append(float(memStore))
        instructionsVec.append(float(instructions))
        fpVectorVec.append(float(fpVector) / 2)
        fpScalarVec.append(float(fpScalar) / 2)
        branchVec.append(float(branchIns))
        froErrVec.append(float(froErr))
    return (
        np.array(elapseTimeVec),
        np.array(memLoadVec),
        np.array(memStoreVec),
        np.array(instructionsVec),
        np.array(fpVectorVec),
        np.array(fpScalarVec),
        np.array(branchVec),
        np.array(froErrVec),
    )


def checkResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/default.csv"
    ruExists = 0
    if os.path.exists(resultFname):
        ruExists = 1
    else:
        print("File does not exist:" + resultFname)
        ruExists = 0
    return ruExists


def checkResultVector(singleValueVec, resultPath):
    resultIsComplete = 0
    for i in singleValueVec:
        resultIsComplete = checkResultSingle(i, resultPath)
        if resultIsComplete == 0:
            return 0
    return 1


def compareMethod(exeSpace, commonPathBase, resultPaths, csvTemplate, algos, dataSetName, reRun=1):
    elapsedTimeAll = []
    memLoadAll = []
    memStoreAll = []
    periodAll = []
    instructionsAll = []
    fpVectorAll = []
    fpScalarAll = []
    branchAll = []
    froErrAll = []
    resultIsComplete = 1
    for i in range(len(algos)):
        resultPath = commonPathBase + resultPaths[i]
        algoTag = algos[i]
        if reRun == 1:
            os.system("sudo rm -rf " + resultPath)
            os.system("sudo mkdir " + resultPath)
            runPeriodVector(exeSpace, algoTag, resultPath, dataSetName, csvTemplate)
        else:
            if reRun == 2:
                resultIsComplete = checkResultVector(dataSetName, resultPath)
                if resultIsComplete == 1:
                    print(algoTag + " is complete, skip")
                else:
                    print(algoTag + " is incomplete, redo it")
                    if os.path.exists(resultPath) == False:
                        os.system("sudo mkdir " + resultPath)
                    runPeriodVector(exeSpace, algoTag, resultPath, dataSetName, csvTemplate, 2)
                    resultIsComplete = checkResultVector(dataSetName, resultPath)
        # exit()
        if resultIsComplete:
            (
                elapsedTime,
                memLoad,
                memStore,
                instructions,
                fpVector,
                fpScalar,
                branchIns,
                froErrVec,
            ) = readResultVector(dataSetName, resultPath)
            elapsedTimeAll.append(elapsedTime)
            memLoadAll.append(memLoad)
            memStoreAll.append(memStore)
            print(resultPaths)
            periodAll.append(dataSetName)
            instructionsAll.append(instructions)
            fpVectorAll.append(fpVector)
            fpScalarAll.append(fpScalar)
            branchAll.append(branchIns)
            froErrAll.append(froErrVec)
        # periodAll.append(periodVec)
    return (
        np.array(elapsedTimeAll),
        np.array(memLoadAll),
        np.array(periodAll),
        np.array(instructionsAll),
        np.array(memStoreAll),
        np.array(fpVectorAll),
        np.array(fpScalarAll),
        np.array(branchAll),
        np.array(froErrAll),
    )


def getCyclesPerMethod(cyclesAll, valueChose):
    instructionsPerMethod = []
    for i in range(len(cyclesAll)):
        instructionsPerMethod.append(cyclesAll[int(i)][int(valueChose)])
    return np.array(instructionsPerMethod)


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    commonBasePath = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/scanZeroMaskAIns/"
    )

    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/scanZeroMaskAIns/"

    # add the datasets here
    # srcAVec=["datasets/AST/mcfe.mtx"] # 765*756
    # srcBVec=["datasets/AST/mcfe.mtx"] # 765*756
    # dataSetNames=['AST']
    # srcAVec=['datasets/UTM/utm1700a.mtx'] # 1700*1700
    # srcBVec=['datasets/UTM/utm1700b.mtx'] # 1700*1700
    # dataSetNames=['UTM']
    # srcAVec=['datasets/ECO/wm2.mtx',"datasets/DWAVE/dwa512.mtx","datasets/AST/mcfe.mtx",'datasets/UTM/utm1700a.mtx','datasets/RDB/rdb2048.mtx','datasets/ZENIOS/zenios.mtx','datasets/QCD/qcda_small.mtx',"datasets/BUS/gemat1.mtx",]
    # srcBVec=['datasets/ECO/wm3.mtx',"datasets/DWAVE/dwb512.mtx","datasets/AST/mcfe.mtx",'datasets/UTM/utm1700b.mtx','datasets/RDB/rdb2048l.mtx','datasets/ZENIOS/zenios.mtx','datasets/QCD/qcdb_small.mtx',"datasets/BUS/gemat1.mtx",]
    # dataSetNames=['ECO','DWAVE','AST','UTM','RDB','ZENIOS','QCD','BUS']
    # srcAVec=['datasets/ECO/wm2.mtx',"datasets/DWAVE/dwa512.mtx","datasets/AST/mcfe.mtx",'datasets/UTM/utm1700a.mtx','datasets/RDB/rdb2048.mtx','datasets/ZENIOS/zenios.mtx','datasets/QCD/qcda_small.mtx',"datasets/BUS/gemat1.mtx",]
    # srcBVec=['datasets/ECO/wm3.mtx',"datasets/DWAVE/dwb512.mtx","datasets/AST/mcfe.mtx",'datasets/UTM/utm1700b.mtx','datasets/RDB/rdb2048l.mtx','datasets/ZENIOS/zenios.mtx','datasets/QCD/qcdb_small.mtx',"datasets/BUS/gemat1.mtx",]
    # nnzAValues= [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
    nnzAValues = [0.1, 0.2, 0.5, 0.8, 1.0]
    # add the algo tag here
    algosVec = [
        "int8",
        "crs",
        "countSketch",
        "cooFD",
        "blockLRA",
        "fastjlt",
        "vq",
        "pq",
        "rip",
        "smp-pca",
        "weighted-cr",
        "tugOfWar",
        "int8_fp32",
        "mm",
    ]
    # algosVec=[ 'crs',  'cooFD','mm']
    algoDisp = [
        "INT8",
        "CRS",
        "CS",
        "CoOFD",
        "BlockLRA",
        "FastJLT",
        "VQ",
        "PQ",
        "RIP",
        "SMP-PCA",
        "WeightedCR",
        "TugOfWar",
        "NLMM",
        "LTMM",
    ]
    # algoDisp=['CRS', 'CoOFD', 'LTMM']
    # add the algo tag here
    # algosVec=['mm', 'crs', 'countSketch', 'int8', 'weighted-cr', 'rip', 'smp-pca', 'tugOfWar', 'blockLRA', 'vq', 'pq', 'fastjlt', 'cooFD', 'int8_fp32']

    # this template configs all algos as lazy mode, all datasets are static and normalized
    csvTemplate = "config_e2e_static_lazy.csv"
    # do not change the following
    resultPaths = algosVec

    # run
    reRun = 0
    if len(sys.argv) < 2:
        os.system("mkdir ../../results")
        os.system("mkdir ../../figures")
        os.system("mkdir " + figPath)
        os.system("sudo rm -rf " + commonBasePath)
        os.system("sudo mkdir " + commonBasePath)
        reRun = 1
    else:
        reRun = int(sys.argv[1])
    print(reRun)
    methodTags = algoDisp
    (
        elapsedTimeAll,
        memLoadAll,
        periodAll,
        instructions,
        memStoreAll,
        fpVectorAll,
        fpScalarAll,
        branchAll,
        froAll,
    ) = compareMethod(
        exeSpace, commonBasePath, resultPaths, csvTemplate, algosVec, nnzAValues, reRun
    )
    # Add some pre-process logic for int8 here if it is used

    print(instructions, memLoadAll)

    # adjust int8: int8/int8_fp32*mm
    # int8_adjust_ratio = instructions[0]/instructions[-2]
    int8_adjust_ratio = 1
    for instruc in [instructions, memLoadAll, memStoreAll, fpVectorAll, fpScalarAll, branchAll]:
        instruc[0] = instruc[-1] * int8_adjust_ratio
    otherIns = instructions - memLoadAll - memStoreAll - fpVectorAll - fpScalarAll
    print(otherIns)
    print(otherIns[0], len(otherIns))
    allowLegend = 1
    valueVec = nnzAValues
    bandInt = []
    for valueChose in range(len(valueVec)):
        instructionsPerMethod = getCyclesPerMethod(instructions, valueChose)
        memLoadPerMethod = (
            getCyclesPerMethod(memLoadAll, valueChose) / instructionsPerMethod * 100.0
        )
        memStorePerMethod = (
            getCyclesPerMethod(memStoreAll, valueChose) / instructionsPerMethod * 100.0
        )
        fpVectorPerMethod = (
            getCyclesPerMethod(fpVectorAll, valueChose) / instructionsPerMethod * 100.0
        )
        fpScalarPerMethod = (
            getCyclesPerMethod(fpScalarAll, valueChose) / instructionsPerMethod * 100.0
        )
        branchPerMethod = getCyclesPerMethod(branchAll, valueChose) / instructionsPerMethod * 100.0
        otherPerMethod = getCyclesPerMethod(otherIns, valueChose) / instructionsPerMethod * 100.0

        if str(valueVec[valueChose]) == "BUS":
            bandInt = branchPerMethod + otherPerMethod
            instructionsPerMethod = getCyclesPerMethod(instructions, valueChose)
            memLoadPerMethod = getCyclesPerMethod(memLoadAll, valueChose)
            memStorePerMethod = getCyclesPerMethod(memStoreAll, valueChose)
            fpVectorPerMethod = getCyclesPerMethod(fpVectorAll, valueChose)
            fpScalarPerMethod = getCyclesPerMethod(fpScalarAll, valueChose)
            prop1 = instructionsPerMethod / instructionsPerMethod[-1]
            fpTemp = fpVectorPerMethod + fpScalarPerMethod
            prop2 = fpTemp / fpTemp[-1]
            memTemp = memLoadPerMethod + memLoadPerMethod
            prop3 = memTemp / memTemp[-1]
            prop4Temp = getCyclesPerMethod(branchAll, valueChose) + getCyclesPerMethod(
                otherIns, valueChose
            )
            prop4 = prop4Temp / prop4Temp[-1]
            groupBar2.DrawFigureYLog2(
                methodTags,
                [prop1, prop2, prop3, prop4],
                ["Total", "FP", "Mem", "Other"],
                "",
                "Instructions (times of LTMM)",
                5,
                15,
                figPath + "/" + "bus_ins_times_ltmm",
                True,
            )

        allowLegend = 0
    exit()
    # draw2yBar(methodTags,[lat95All[0][0],lat95All[1][0],lat95All[2][0],lat95All[3][0]],[errAll[0][0],errAll[1][0],errAll[2][0],errAll[3][0]],'95% latency (ms)','Error (%)',figPath + "sec6_5_stock_q1_normal")
    # groupBar2.DrawFigure(dataSetNames, errAll, methodTags, "Datasets", "Error (%)", 5, 15, figPath + "sec4_1_e2e_static_lazy_fro", True)
    # groupBar2.DrawFigure(dataSetNames, np.log(lat95All), methodTags, "Datasets", "95% latency (ms)", 5, 15, figPath + "sec4_1_e2e_static_lazy_latency_log", True)
    fpInsAll = fpVectorAll + fpScalarAll
    ratioFpIns = fpVectorAll / fpInsAll * 100.0
    memInsAll = memLoadAll + memStoreAll
    # groupBar2.DrawFigureYLog(nnzAValues, instructions/instructions[-1], methodTags, "Datasets", "Ins (times of LTMM)", 5, 15, figPath + "/" + "instructions", True)
    # groupBar2.DrawFigureYLog(nnzAValues, fpInsAll/fpInsAll[-1], methodTags, "Datasets", "FP Ins (times of LTMM)", 5, 15, figPath + "/" + "FP_instructions", True)
    # groupBar2.DrawFigureYLog(nnzAValues, memInsAll/memInsAll[-1], methodTags, "Datasets", "Mem Ins (times of LTMM)", 5, 15, figPath + "/" + "mem_instructions", True)
    # groupBar2.DrawFigure(nnzAValues, ratioFpIns, methodTags, "Datasets", "SIMD Utilization (%)", 5, 15, figPath + "/" + "SIMD utilization", True)
    # groupBar2.DrawFigure(nnzAValues, instructions/(memLoadAll+memStoreAll), methodTags, "Datasets", "IPM", 5, 15, figPath + "/" + "IPM", True)
    # groupBar2.DrawFigure(nnzAValues, fpInsAll/(memLoadAll+memStoreAll), methodTags, "Datasets", "FP Ins per Unit Mem Access", 5, 15, figPath + "/" + "FPIPM", True)
    # groupBar2.DrawFigure(nnzAValues, (memLoadAll+memStoreAll)/(instructions)*100.0, methodTags, "Datasets", "Ratio of Mem Ins (%)", 5, 15, figPath + "/" + "mem", True)

    # groupBar2.DrawFigure(nnzAValues, branchAll/instructions*100.0, methodTags, "Datasets", "Ratio of Branch Ins (%)", 5, 15, figPath + "/" + "branches", True)
    # groupBar2.DrawFigure(nnzAValues, otherIns/instructions*100.0, methodTags, "Datasets", "Ratio of Other Ins (%)", 5, 15, figPath + "/" + "others", True)
    # print(instructions[-1],instructions[2])

    # groupBar2.DrawFigure(dataSetNames, np.log(thrAll), methodTags, "Datasets", "elements/ms", 5, 15, figPath + "sec4_1_e2e_static_lazy_throughput_log", True)
    groupLine.DrawFigureYnormal(
        periodAll,
        elapsedTimeAll,
        methodTags,
        "nnz ratio",
        "95% latency (ms)",
        0,
        1,
        figPath + "/" + "nnz_lat",
        True,
    )
    groupLine.DrawFigureYnormal(
        periodAll,
        froAll,
        methodTags,
        "nnz ratio",
        "fro error (%)",
        0,
        1,
        figPath + "/" + "nnz_err",
        True,
    )
    groupLine.DrawFigureYnormal(
        periodAll,
        (memInsAll) / instructions * 100.0,
        methodTags,
        "nnz ratio",
        "propotion of mem access (%)",
        0,
        1,
        figPath + "/" + "nnz_mem",
        True,
    )
    groupLine.DrawFigureYnormal(
        periodAll,
        (branchAll) / instructions * 100.0,
        methodTags,
        "nnz ratio",
        "propotion of branch (%)",
        0,
        1,
        figPath + "/" + "nnz_branch",
        True,
    )
    groupLine.DrawFigureYnormal(
        periodAll,
        (otherIns) / instructions * 100.0,
        methodTags,
        "nnz ratio",
        "propotion of others (%)",
        0,
        1,
        figPath + "/" + "nnz_other",
        True,
    )


if __name__ == "__main__":
    main()
