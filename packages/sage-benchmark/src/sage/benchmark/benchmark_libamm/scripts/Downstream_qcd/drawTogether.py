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
LABEL_V = FontProperties(style="normal", size=LABEL_FONT_SIZE)
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
    "QCD": 3072,
}


def runPeriod(
    exePath, srcA, srcB, algoTag, resultPath, configTemplate="config.csv", prefixTag="null"
):
    # resultFolder="periodTests"
    configFname = "config_period_" + prefixTag + ".csv"
    configTemplate = "config_e2e_static_lazy.csv"
    # clear old files
    os.system("cd " + exePath + "&& sudo rm *.csv")
    os.system("cp perfListEvaluation.csv " + exePath)
    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    editConfig(configTemplate, exePath + "temp1.csv", "srcA", srcA)
    editConfig(exePath + "temp1.csv", exePath + "temp2.csv", "srcB", srcB)
    editConfig(exePath + "temp2.csv", exePath + "temp1.csv", "sketchDimension", 307)
    editConfig(exePath + "temp1.csv", exePath + "temp2.csv", "cppAlgoTag", algoTag)

    # int8 or int8_fp32
    if algoTag == "int8_fp32":
        editConfig(exePath + "temp2.csv", exePath + configFname, "fpMode", "fp32")
    else:
        editConfig(exePath + "temp2.csv", exePath + configFname, "fpMode", "INT8")

    os.system("cd " + exePath + "&& rm *.pth")
    os.system("cp *.pth " + exePath)
    # prepare new file
    # run
    os.system(
        "export OMP_NUM_THREADS=1 &&" + "cd " + exePath + "&& sudo ./benchmarkQCD " + configFname
    )
    # copy result
    os.system("sudo rm -rf " + resultPath + "/" + str(prefixTag))
    os.system("sudo mkdir " + resultPath + "/" + str(prefixTag))
    os.system("cd " + exePath + "&& sudo cp *.csv " + resultPath + "/" + str(prefixTag))


def runPeriodVector(
    exePath, periodVec, pS, algoTag, resultPath, prefixTag, configTemplate="config.csv", reRun=1
):
    for i in range(len(periodVec)):
        rf = periodVec[i]
        sf = pS[i]
        print(sf)
        if reRun == 2:
            if checkResultSingle(prefixTag[i], resultPath) == 1:
                print("skip " + prefixTag[i])
            else:
                runPeriod(exePath, rf, sf, algoTag, resultPath, configTemplate, prefixTag[i])
        else:
            runPeriod(exePath, rf, sf, algoTag, resultPath, configTemplate, prefixTag[i])


def readResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/default.csv"
    elapsedTime = readConfig(resultFname, "perfElapsedTime")
    cpuCycle = 0
    memStall = 0
    instructions = 0
    ammErro = readConfig(resultFname, "froError")
    endError = readConfig(resultFname, "qcdError")
    l3Stall = 0
    totalStall = 0
    return elapsedTime, cpuCycle, memStall, instructions, ammErro, endError, l3Stall, totalStall


def checkResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/default.csv"
    ruExists = 0
    if os.path.exists(resultFname):
        ruExists = 1
    else:
        print("File does not exist:" + resultFname)
        ruExists = 0
    return ruExists


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    cpuCycleVec = []
    memStallVec = []
    instructionsVec = []
    ammErroVec = []
    endErrorVec = []
    l3StallVec = []
    totalStallVec = []
    for i in singleValueVec:
        elapsedTime, cpuCycle, memStall, instructions, ammErro, endError, l3Stall, totalStall = (
            readResultSingle(i, resultPath)
        )
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        cpuCycleVec.append(float(cpuCycle))
        memStallVec.append(float(memStall))
        instructionsVec.append(float(instructions))
        ammErroVec.append(float(ammErro))
        endErrorVec.append(float(endError))
        l3StallVec.append(float(l3Stall))
        totalStallVec.append(float(totalStall))
    return (
        np.array(elapseTimeVec),
        np.array(cpuCycleVec),
        np.array(memStallVec),
        np.array(instructionsVec),
        np.array(ammErroVec),
        np.array(endErrorVec),
        np.array(l3StallVec),
        np.array(totalStallVec),
    )


def readResultVectorNull(singleValueVec, resultPath):
    elapseTimeVec = []
    cpuCycleVec = []
    memStallVec = []
    instructionsVec = []
    ammErroVec = []
    endErrorVec = []
    l3StallVec = []
    totalStallVec = []
    for i in singleValueVec:
        elapseTimeVec.append(0.0)
        cpuCycleVec.append(0.0)
        memStallVec.append(0.0)
        instructionsVec.append(0.0)
        ammErroVec.append(0.0)
        endErrorVec.append(0.0)
        l3StallVec.append(0.0)
        totalStallVec.append(0.0)
    return (
        np.array(elapseTimeVec),
        np.array(cpuCycleVec),
        np.array(memStallVec),
        np.array(instructionsVec),
        np.array(ammErroVec),
        np.array(endErrorVec),
        np.array(l3StallVec),
        np.array(totalStallVec),
    )


def checkResultVector(singleValueVec, resultPath):
    resultIsComplete = 0
    for i in singleValueVec:
        resultIsComplete = checkResultSingle(i, resultPath)
        if resultIsComplete == 0:
            return 0
    return 1


def isValidAlgoTag(algoTag):
    invalidTags = ["vqq", "pqq"]
    for i in invalidTags:
        if algoTag == i:
            return False
    return True


def compareMethod(
    exeSpace,
    commonPathBase,
    resultPaths,
    csvTemplate,
    srcAVec,
    srcBVec,
    algos,
    dataSetName,
    reRun=1,
):
    elapsedTimeAll = []
    cpuCycleAll = []
    memStallAll = []
    periodAll = []
    instructionsAll = []
    ammErroAll = []
    endErrorAll = []
    l3StallAll = []
    totalStallAll = []
    resultIsComplete = 1
    for i in range(len(algos)):
        resultPath = commonPathBase + resultPaths[i]
        algoTag = algos[i]
        if reRun == 1:
            os.system("sudo rm -rf " + resultPath)
            os.system("sudo mkdir " + resultPath)
            if isValidAlgoTag(algoTag):
                runPeriodVector(
                    exeSpace, srcAVec, srcBVec, algoTag, resultPath, dataSetName, csvTemplate
                )
        else:
            if reRun == 2:
                resultIsComplete = checkResultVector(dataSetName, resultPath)
                if resultIsComplete == 1:
                    print(algoTag + " is complete, skip")
                else:
                    if isValidAlgoTag(algoTag):
                        print(algoTag + " is incomplete, redo it")
                        if os.path.exists(resultPath) == False:
                            os.system("sudo mkdir " + resultPath)
                        runPeriodVector(
                            exeSpace,
                            srcAVec,
                            srcBVec,
                            algoTag,
                            resultPath,
                            dataSetName,
                            csvTemplate,
                            2,
                        )
                        resultIsComplete = checkResultVector(dataSetName, resultPath)
                    else:
                        print(algoTag + " is invalid, skip")
                        resultIsComplete = 1

        # exit()
        if resultIsComplete:
            if isValidAlgoTag(algoTag):
                (
                    elapsedTime,
                    cpuCycle,
                    memStall,
                    instructions,
                    ammErro,
                    endError,
                    l3Stall,
                    totalStall,
                ) = readResultVector(dataSetName, resultPath)
            else:
                (
                    elapsedTime,
                    cpuCycle,
                    memStall,
                    instructions,
                    ammErro,
                    endError,
                    l3Stall,
                    totalStall,
                ) = readResultVectorNull(dataSetName, resultPath)
            elapsedTimeAll.append(elapsedTime)
            cpuCycleAll.append(cpuCycle)
            memStallAll.append(memStall)
            periodAll.append(elapsedTime)
            instructionsAll.append(instructions)
            ammErroAll.append(ammErro)
            endErrorAll.append(endError)
            l3StallAll.append(l3Stall)
            totalStallAll.append(totalStall)
        # periodAll.append(periodVec)
    return (
        np.array(elapsedTimeAll),
        np.array(cpuCycleAll),
        np.array(periodAll),
        np.array(instructionsAll),
        np.array(memStallAll),
        np.array(ammErroAll),
        np.array(endErrorAll),
        np.array(l3StallAll),
        np.array(totalStallAll),
    )


def getCyclesPerMethod(cyclesAll, valueChose):
    instructionsPerMethod = []
    for i in range(len(cyclesAll)):
        instructionsPerMethod.append(cyclesAll[int(i)][int(valueChose)])
    return np.array(instructionsPerMethod)


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    commonBasePath = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/Downstream_QCD/"
    )

    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/Downstream_QCD/"

    # add the datasets here
    # srcAVec=["datasets/AST/mcfe.mtx"] # 765*756
    # srcBVec=["datasets/AST/mcfe.mtx"] # 765*756
    # dataSetNames=['AST']
    # srcAVec=['datasets/UTM/utm1700a.mtx'] # 1700*1700
    # srcBVec=['datasets/UTM/utm1700b.mtx'] # 1700*1700
    # dataSetNames=['UTM']
    # algosVec=['crs', 'mm']
    # algoDisp=['CRS','LTMM']
    # algoDisp=['INT8', 'CRS', 'CS', 'CoOFD', 'BlockLRA', 'FastJLT', 'VQ', 'PQ', 'RIP', 'SMP-PCA', 'WeightedCR', 'TugOfWar',  'NLMM', 'LTMM']
    srcAVec = ["datasets/QCD/qcda_small.mtx"]
    srcBVec = ["datasets/QCD/qcda_small.mtx"]
    dataSetNames = ["QCD"]
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
    # srcAVec=['datasets/ECO/wm2.mtx',"datasets/DWAVE/dwa512.mtx","datasets/AST/mcfe.mtx",'datasets/UTM/utm1700a.mtx','datasets/RDB/rdb2048.mtx','datasets/ZENIOS/zenios.mtx','datasets/QCD/qcda_small.mtx',"datasets/BUS/gemat1.mtx",]
    # srcBVec=['datasets/ECO/wm3.mtx',"datasets/DWAVE/dwb512.mtx","datasets/AST/mcfe.mtx",'datasets/UTM/utm1700b.mtx','datasets/RDB/rdb2048l.mtx','datasets/ZENIOS/zenios.mtx','datasets/QCD/qcdb_small.mtx',"datasets/BUS/gemat1.mtx",]
    # dataSetNames=['ECO','DWAVE','AST','UTM','RDB','ZENIOS','QCD','BUS']
    # add the algo tag here
    # algosVec=[ 'crs']
    # algoDisp=[ 'CRS']
    # algosVec=[ 'smp-pca']
    # algoDisp=[ 'SMP-PCA']
    # add the algo tag here
    # algosVec=['mm', 'crs', 'countSketch', 'int8', 'weighted-cr', 'rip', 'smp-pca', 'tugOfWar', 'blockLRA', 'vq', 'pq', 'fastjlt', 'cooFD', 'int8_fp32']

    # this template configs all algos as lazy mode, all datasets are static and normalized
    csvTemplate = "config_e2e_static_lazy.csv"
    # do not change the following
    resultPaths = algosVec
    # tryQCD(exeSpace)
    # exit()
    # run
    reRun = 0
    os.system("mkdir ../../results")
    os.system("mkdir ../../figures")
    os.system("mkdir " + figPath)
    if len(sys.argv) < 2:
        os.system("sudo rm -rf " + commonBasePath)
        os.system("sudo mkdir " + commonBasePath)
        reRun = 1
    else:
        reRun = int(sys.argv[1])
    os.system("sudo mkdir " + commonBasePath)
    print(reRun)
    # exit()
    methodTags = algoDisp
    (
        elapsedTimeAll,
        cpuCycleAll,
        periodAll,
        instructions,
        memStallAll,
        ammErroAll,
        endErrorAll,
        l3StallAll,
        totalStallAll,
    ) = compareMethod(
        exeSpace,
        commonBasePath,
        resultPaths,
        csvTemplate,
        srcAVec,
        srcBVec,
        algosVec,
        dataSetNames,
        reRun,
    )
    # Add some pre-process logic for int8 here if it is used

    # groupBar2.DrawFigure(dataSetNames,(ammErroAll+endErrorAll+l3StallAll)/cpuCycleAll*100.0,methodTags, "Datasets", "Ratio of cacheStalls (%)", 5, 15, figPath + "cachestall_ratio", True)
    for instruc in [elapsedTimeAll]:
        instruc = np.maximum(instruc, 0)
        int8_adjust_ratio = instruc[0] / instruc[-2]
        instruc[0] = instruc[-1] * int8_adjust_ratio
    int8_adjust_ratio = elapsedTimeAll[0] / elapsedTimeAll[-2]
    elapsedTimeAll[0] = elapsedTimeAll[-1] * int8_adjust_ratio
    ammErroAll[-2] = ammErroAll[-2] - ammErroAll[-2]

    # groupBar2.DrawFigure(dataSetNames, np.log(thrAll), methodTags, "Datasets", "elements/ms", 5, 15, figPath + "sec4_1_e2e_static_lazy_throughput_log", True)


if __name__ == "__main__":
    main()
