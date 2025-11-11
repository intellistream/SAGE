#!/usr/bin/env python3
import os

import accuBar as accuBar
import groupBar2 as groupBar2
import groupLine as groupLine
import matplotlib
import numpy as np
from matplotlib.font_manager import FontProperties
from OoOCommon import *  # noqa: F403  # noqa: F403
from OoOCommon import editConfig, readConfig

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


def runPeriod(exePath, algoTag, resultPath, configTemplate="config.csv", prefixTagRaw="null"):
    # resultFolder="periodTests"
    prefixTag = str(prefixTagRaw)
    configFname = "config_period_" + str(prefixTag) + ".csv"
    configTemplate = "config_e2e_static_lazy.csv"
    # clear old files
    os.system("cd " + exePath + "&& sudo rm *.csv")
    os.system("cp perfListEvaluation.csv " + exePath)
    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    editConfig(configTemplate, exePath + "temp1.csv", "zipfAlphaA", prefixTag)
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
        # pqvqCodewordLookUpTablePath = glob.glob(f'{pqvqCodewordLookUpTableDir}/{prefixTag}_m1_row*')[0]
        pqvqCodewordLookUpTablePath = glob.glob(f"{pqvqCodewordLookUpTableDir}/1000_m1_row*")[0]
    elif algoTag == "pq":
        # pqvqCodewordLookUpTablePath = glob.glob(f'{pqvqCodewordLookUpTableDir}/{prefixTag}_m10_row*')[0]
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
                print("skip " + str(prefixTag[i]))
            else:
                runPeriod(exePath, algoTag, resultPath, configTemplate, prefixTag[i])
        else:
            runPeriod(exePath, algoTag, resultPath, configTemplate, prefixTag[i])


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
    froErr = readConfig(resultFname, "froError")
    return (
        elapsedTime,
        cpuCycle,
        memStall,
        instructions,
        l1dStall,
        l2Stall,
        l3Stall,
        totalStall,
        froErr,
    )


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
            fro,
        ) = readResultSingle(i, resultPath)
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        cpuCycleVec.append(float(cpuCycle))
        memStallVec.append(float(memStall))
        instructionsVec.append(float(instructions))
        l1dStallVec.append(float(l1dStall))
        l2StallVec.append(float(l2Stall))
        l3StallVec.append(float(l3Stall))
        totalStallVec.append(float(totalStall))
        froVec.append(float(fro))
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
    algoCnt = 0
    for i in range(len(algos)):
        resultPath = commonPathBase + resultPaths[i]
        algoTag = algos[i]
        scanVec = dataSetName
        if reRun == 1:
            os.system("sudo rm -rf " + resultPath)
            os.system("sudo mkdir " + resultPath)
            runPeriodVector(exeSpace, algoTag, resultPath, scanVec, csvTemplate)
        else:
            if reRun == 2:
                resultIsComplete = checkResultVector(scanVec, resultPath)
                if resultIsComplete == 1:
                    print(algoTag + " is complete, skip")
                else:
                    print(algoTag + " is incomplete, redo it")
                    if not os.path.exists(resultPath):
                        os.system("sudo mkdir " + resultPath)
                    runPeriodVector(exeSpace, algoTag, resultPath, scanVec, csvTemplate, 2)
                    resultIsComplete = checkResultVector(scanVec, resultPath)
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
                froVec,
            ) = readResultVector(dataSetName, resultPath)
            elapsedTimeAll.append(elapsedTime)
            cpuCycleAll.append(cpuCycle)
            memStallAll.append(memStall)
            periodAll.append(dataSetName)
            instructionsAll.append(instructions)
            l1dStallAll.append(l1dStall)
            l2StallAll.append(l2Stall)
            l3StallAll.append(l3Stall)
            totalStallAll.append(totalStall)
            froAll.append(froVec)
            algoCnt = algoCnt + 1
            print(algoCnt)
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


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    commonBasePath = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/scanAZipfCycles/"
    )

    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/scanAZipfCycles"

    aGuassianVec = [1.2, 1.3]
    # aGuassianVec=[100, 200, 500, 1000]
    # add the algo tag here
    # algosVec=['int8', 'crs', 'countSketch', 'cooFD', 'blockLRA', 'fastjlt', 'vq', 'pq', 'rip', 'smp-pca', 'weighted-cr', 'tugOfWar', 'int8_fp32', 'mm']
    algosVec = ["crs", "countSketch", "blockLRA", "fastjlt", "rip", "smp-pca", "tugOfWar"]
    # algosVec=[ 'crs']
    # algoDisp=['CRS']
    # add the algo tag here

    # this template configs all algos as lazy mode, all datasets are static and normalized
    csvTemplate = "config_e2e_static_lazy.csv"
    # do not change the following
    resultPaths = algosVec
    os.system("mkdir ../../results")
    os.system("mkdir ../../figures")
    os.system("mkdir " + figPath)
    # run
    reRun = 2
    os.system("sudo mkdir " + commonBasePath)
    print(reRun)
    (
        elapsedTimeAll,
        cpuCycleAll,
        periodAll,
        instructions,
        memStallAll,
        l1dStallAll,
        l2StallAll,
        l3StallAll,
        totalStallAll,
        froAll,
    ) = compareMethod(
        exeSpace, commonBasePath, resultPaths, csvTemplate, algosVec, aGuassianVec, reRun
    )
    # Add some pre-process logic for int8 here if it is used

    groupLine.DrawFigureYnormal(
        periodAll,
        elapsedTimeAll,
        methodTags,
        "Zipf factor",
        r"Processing Latency l (ms)",
        0,
        1,
        figPath + "/" + "aZipf_lat_large",
        True,
    )
    groupLine.DrawFigureYSub(
        periodAll, froAll, methodTags, "", "", 0, 1, figPath + "/" + "aZipf_err_small", False
    )

    # Add some pre-process logic for int8 here if it is used


if __name__ == "__main__":
    main()
