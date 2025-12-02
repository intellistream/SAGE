#!/usr/bin/env python3
import os

import accuBar as accuBar
import drawBuild
import drawSearch
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


def runPeriod(exePath, algoTag, resultPath, configTemplate="config.csv", prefixTagRaw="null"):
    # resultFolder="periodTests"
    prefixTag = str(prefixTagRaw)
    configFname = "config_period_" + str(prefixTag) + ".csv"
    configTemplate = "config_e2e_static_lazy.csv"
    # clear old files
    os.system("cd " + exePath + "&& sudo rm *.csv")
    os.system("cp perfListEvaluation.csv " + exePath)

    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    editConfig(configTemplate, exePath + "temp1.csv", "vectorDim", prefixTag)
    exeTag = algoTag
    if algoTag == "PQ-Rebuild":
        exeTag = "incrementalPQ"
        editConfig(exePath + "temp1.csv", exePath + "temp2.csvfullReBuild", 1)
        editConfig(exePath + "temp2.csv", exePath + "temp1.csvfullReBuild", 1)
    # prepare new file
    # run
    os.system(
        "export OMP_NUM_THREADS=1 &&" + "cd " + exePath + "&& sudo ./" + exeTag + " " + "temp1.csv"
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
    resultFname = resultPath + "/" + str(singleValue) + "/result.csv"
    elapsedTime = readConfig(resultFname, "brutalForceBuild")
    incrementalBuild = readConfig(resultFname, "incrementalBuild")
    incrementalSearch = readConfig(resultFname, "incrementalSearch")
    recall = readConfig(resultFname, "recall")
    l1dStall = 0
    l2Stall = 0
    l3Stall = 0
    totalStall = 0
    froErr = 0
    return (
        elapsedTime,
        incrementalBuild,
        incrementalSearch,
        recall,
        l1dStall,
        l2Stall,
        l3Stall,
        totalStall,
        froErr,
    )


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    incrementalBuildVec = []
    incrementalSearchVec = []
    recallVec = []
    l1dStallVec = []
    l2StallVec = []
    l3StallVec = []
    totalStallVec = []
    froVec = []
    for i in singleValueVec:
        (
            elapsedTime,
            incrementalBuild,
            incrementalSearch,
            recall,
            l1dStall,
            l2Stall,
            l3Stall,
            totalStall,
            fro,
        ) = readResultSingle(i, resultPath)
        elapseTimeVec.append(float(elapsedTime))
        incrementalBuildVec.append(float(incrementalBuild))
        incrementalSearchVec.append(float(incrementalSearch))
        recallVec.append(float(recall))
        l1dStallVec.append(float(l1dStall))
        l2StallVec.append(float(l2Stall))
        l3StallVec.append(float(l3Stall))
        totalStallVec.append(float(totalStall))
        froVec.append(float(fro))
    return (
        np.array(elapseTimeVec),
        np.array(incrementalBuildVec),
        np.array(incrementalSearchVec),
        np.array(recallVec),
        np.array(l1dStallVec),
        np.array(l2StallVec),
        np.array(l3StallVec),
        np.array(totalStallVec),
        np.array(froVec),
    )


def checkResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/result.csv"
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
    incrementalBuildAll = []
    incrementalSearchAll = []
    periodAll = []
    recallAll = []
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
                    if os.path.exists(resultPath) == False:
                        os.system("sudo mkdir " + resultPath)
                    runPeriodVector(exeSpace, algoTag, resultPath, scanVec, csvTemplate, 2)
                    resultIsComplete = checkResultVector(scanVec, resultPath)
        # exit()
        if resultIsComplete:
            (
                elapsedTime,
                incrementalBuild,
                incrementalSearch,
                recall,
                l1dStall,
                l2Stall,
                l3Stall,
                totalStall,
                froVec,
            ) = readResultVector(dataSetName, resultPath)
            elapsedTimeAll.append(elapsedTime)
            incrementalBuildAll.append(incrementalBuild)
            incrementalSearchAll.append(incrementalSearch)
            periodAll.append(dataSetName)
            recallAll.append(recall)
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
        np.array(incrementalBuildAll),
        np.array(periodAll),
        np.array(recallAll),
        np.array(incrementalSearchAll),
        np.array(l1dStallAll),
        np.array(l2StallAll),
        np.array(l3StallAll),
        np.array(totalStallAll),
        np.array(froAll),
    )


def getCyclesPerMethod(cyclesAll, valueChose):
    recallPerMethod = []
    for i in range(len(cyclesAll)):
        recallPerMethod.append(cyclesAll[int(i)][int(valueChose)])
    return np.array(recallPerMethod)


def main():
    drawSearch.main()
    drawBuild.main()


if __name__ == "__main__":
    main()
