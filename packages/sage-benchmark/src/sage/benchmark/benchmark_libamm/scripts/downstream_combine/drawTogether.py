#!/usr/bin/env python3
import os

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
    "AST": 765,
    "BUS": 10595,
    "DWAVE": 512,
    "ECO": 260,
    "QCD": 3072,
    "RDB": 2048,
    "UTM": 1700,
    "ZENIOS": 2873,
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
    editConfig(
        exePath + "temp2.csv",
        exePath + "temp1.csv",
        "sketchDimension",
        int(dataset_acols_mapping[prefixTag] * 0.1),
    )
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
        pqvqCodewordLookUpTablePath = glob.glob(f"{pqvqCodewordLookUpTableDir}/{prefixTag}_m1_*")[0]
    elif algoTag == "pq":
        pqvqCodewordLookUpTablePath = glob.glob(f"{pqvqCodewordLookUpTableDir}/{prefixTag}_m10_*")[
            0
        ]
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
    cpuCycle = readConfig(resultFname, "cpuCycle")
    memStall = readConfig(resultFname, "memStall")
    instructions = readConfig(resultFname, "instructions")
    l1dStall = readConfig(resultFname, "l1dStall")
    l2Stall = readConfig(resultFname, "l2Stall")
    l3Stall = readConfig(resultFname, "l3Stall")
    totalStall = readConfig(resultFname, "totalStall")
    froError = readConfig(resultFname, "froError")
    return (
        elapsedTime,
        cpuCycle,
        memStall,
        instructions,
        l1dStall,
        l2Stall,
        l3Stall,
        totalStall,
        froError,
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


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    cpuCycleVec = []
    memStallVec = []
    instructionsVec = []
    l1dStallVec = []
    l2StallVec = []
    l3StallVec = []
    totalStallVec = []
    froVec = []
    for i in singleValueVec:
        (
            elapsedTime,
            cpuCycle,
            memStall,
            instructions,
            l1dStall,
            l2Stall,
            l3Stall,
            totalStall,
            froErr,
        ) = readResultSingle(i, resultPath)
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        cpuCycleVec.append(float(cpuCycle))
        memStallVec.append(float(memStall))
        instructionsVec.append(float(instructions))
        l1dStallVec.append(float(l1dStall))
        l2StallVec.append(float(l2Stall))
        l3StallVec.append(float(l3Stall))
        totalStallVec.append(float(totalStall))
        froVec.append(float(froErr))
    return (
        np.array(elapseTimeVec),
        np.array(cpuCycleVec),
        np.array(memStallVec),
        np.array(instructionsVec),
        np.array(l1dStallVec),
        np.array(l2StallVec),
        np.array(l3StallVec),
        np.array(totalStallVec),
        np.array(froVec),
    )


def checkResultVector(singleValueVec, resultPath):
    resultIsComplete = 0
    for i in singleValueVec:
        resultIsComplete = checkResultSingle(i, resultPath)
        if resultIsComplete == 0:
            return 0
    return 1


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
    l1dStallAll = []
    l2StallAll = []
    l3StallAll = []
    totalStallAll = []
    froAll = []
    resultIsComplete = 1
    for i in range(len(algos)):
        resultPath = commonPathBase + resultPaths[i]
        algoTag = algos[i]
        if reRun == 1:
            os.system("sudo rm -rf " + resultPath)
            os.system("sudo mkdir " + resultPath)
            runPeriodVector(
                exeSpace, srcAVec, srcBVec, algoTag, resultPath, dataSetName, csvTemplate
            )
        else:
            if reRun == 2:
                resultIsComplete = checkResultVector(dataSetName, resultPath)
                if resultIsComplete == 1:
                    print(algoTag + " is complete, skip")
                else:
                    print(algoTag + " is incomplete, redo it")
                    if os.path.exists(resultPath) == False:
                        os.system("sudo mkdir " + resultPath)
                    runPeriodVector(
                        exeSpace, srcAVec, srcBVec, algoTag, resultPath, dataSetName, csvTemplate, 2
                    )
                    resultIsComplete = checkResultVector(dataSetName, resultPath)

        # exit()
        if resultIsComplete:
            (
                elapsedTime,
                cpuCycle,
                memStall,
                instructions,
                l1dStall,
                l2Stall,
                l3Stall,
                totalStall,
                fro,
            ) = readResultVector(dataSetName, resultPath)
            elapsedTimeAll.append(elapsedTime)
            cpuCycleAll.append(cpuCycle)
            memStallAll.append(memStall)
            periodAll.append(elapsedTime)
            instructionsAll.append(instructions)
            l1dStallAll.append(l1dStall)
            l2StallAll.append(l2Stall)
            l3StallAll.append(l3Stall)
            totalStallAll.append(totalStall)
            froAll.append(fro)
        # periodAll.append(periodVec)
    return (
        np.array(elapsedTimeAll),
        np.array(cpuCycleAll),
        np.array(periodAll),
        np.array(instructionsAll),
        np.array(memStallAll),
        np.array(l1dStallAll),
        np.array(l2StallAll),
        np.array(l3StallAll),
        np.array(totalStallAll),
        np.array(froAll),
    )


def getCyclesPerMethod(cyclesAll, valueChose):
    instructionsPerMethod = []
    for i in range(len(cyclesAll)):
        instructionsPerMethod.append(cyclesAll[int(i)][int(valueChose)])
    return np.array(instructionsPerMethod)


def combinDownStream(l1, l2):
    ru = l1.tolist()
    lt = l2.tolist()
    for i in range(len(l1)):
        for j in range(len(lt[i])):
            ru[i].append(lt[i][j])
    return np.array(ru)


def combinTrainning(l1, l2):
    ru = l1.tolist()
    lt = l2.tolist()
    for i in range(len(l1)):
        ru[i].append(lt[i])
    return np.array(ru)


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    # share the same result with cycle breakdown evaluation, as it contains everything
    commonBasePath = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/cycles_breakdown_1/"
    )

    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/downstreamCombine/"
    import drawCCA
    import drawInference
    import drawPCA
    import drawTraining

    procLat, ammError, endError = drawPCA.main()
    i = 0
    while i < 4:
        procLat2 = []
        ammError2 = []
        endError2 = []
        if i == 0:
            procLat2, ammError2, endError2 = drawCCA.main()
            print(len(ammError2))
        if i == 1:
            procLat2, endError2, ammError2, temp, temp2, temp3 = drawTraining.main()
            print(ammError2)
            # print(procLat2)
            # exit()
        # D= 2000
        if i == 2:
            temp, temp2, temp3, procLat2, endError2, ammError2 = drawTraining.main()
            print(ammError2)
            # print(procLat2)
            # exit()
        if i == 3:
            procLat2, ammError2, endError2 = drawInference.main()
        if not (i == 1 or i == 2):
            ammError = combinDownStream(ammError, ammError2)
            procLat = combinDownStream(procLat, procLat2)
            endError = combinDownStream(endError, endError2)
        else:
            procLat = combinTrainning(procLat, procLat2)
            endError = combinTrainning(endError, endError2)
            print(len(endError), len(endError2))
            print(len(ammError), len(ammError2))
            ammError = combinTrainning(ammError, ammError2)
        i = i + 1
    print(endError)
    # exit()
    os.system("mkdir ../../results")
    os.system("mkdir ../../figures")
    os.system("mkdir " + figPath)
    taskNames = [
        "PCA",
        "CCA",
        "Training\n(500-D)",
        "Training\n(2000-D)",
        "Inference\n(CIFAR10)",
        "Inference\n(CIFAR100)",
    ]
    taskNamesShort = ["PCA", "CCA", "Inference\n(CIFAR10)", "Inference\n(CIFAR100)"]
    methodTags = [
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
    groupBar2.DrawFigureYLog(
        taskNames,
        procLat,
        methodTags,
        "Task",
        r"Processing Latency l (ms)",
        5,
        15,
        figPath + "ds_latency",
        True,
    )
    groupBar2.DrawFigureYLog(
        taskNames,
        ammError,
        methodTags,
        "Task",
        r"AMM Error $\epsilon$ ",
        5,
        15,
        figPath + "ds_amm_error",
        False,
    )
    groupBar2.DrawFigureYLog(
        taskNames,
        endError,
        methodTags,
        "Task",
        r"Ending Error $e$ ",
        5,
        15,
        figPath + "ds_app_error",
        False,
    )
    # print(ipcAll)
    # groupBar2.DrawFigure(dataSetNames,(l1dStallAll+l2StallAll+l3StallAll)/cpuCycleAll*100.0,methodTags, "Datasets", "Ratio of cacheStalls (%)", 5, 15, figPath + "cachestall_ratio", True)

    # groupBar2.DrawFigure(dataSetNames, np.log(thrAll), methodTags, "Datasets", "elements/ms", 5, 15, figPath + "sec4_1_e2e_static_lazy_throughput_log", True)


if __name__ == "__main__":
    main()
