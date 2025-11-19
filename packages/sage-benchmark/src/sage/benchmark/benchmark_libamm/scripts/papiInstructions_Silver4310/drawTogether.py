#!/usr/bin/env python3
import os
import sys

import accuBar as accuBar
import groupBar as groupBar
import groupBar2 as groupBar2
import groupLine as groupLine
import matplotlib
import numpy as np
from matplotlib.font_manager import FontProperties
from OoOCommon import *  # noqa: F403  # noqa: F403
from OoOCommon import editConfig, readConfig

# OPT_FONT_NAME = 'Helvetica'
TICK_FONT_SIZE = 22
LABEL_FONT_SIZE = 28
LEGEND_FONT_SIZE = 30
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

scanTag = "aCol"


def singleRun(exePath, singleValue, resultPath, configTemplate):
    # resultFolder="singleValueTests"
    configFname = "config_" + scanTag + str(singleValue) + ".csv"
    # configTemplate = "config.csv"
    # clear old files

    os.system("cd " + exePath + "&& sudo rm default*.csv config*.csv *result*.csv perf*.csv")
    os.system("cp perfListEvaluation.csv " + exePath)
    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    editConfig(configTemplate, exePath + configFname, scanTag, singleValue)
    # prepare new file
    # run
    os.system(
        "export OMP_NUM_THREADS=1 &&" + "cd " + exePath + "&& sudo ./benchmark " + configFname
    )
    # copy result
    os.system("sudo rm -rf " + resultPath + "/" + str(singleValue))
    os.system("sudo mkdir " + resultPath + "/" + str(singleValue))
    os.system("cd " + exePath + "&& sudo cp *.csv " + resultPath + "/" + str(singleValue))


def runScanVector(exePath, singleValueVec, resultPath, templateName="config.csv"):
    for i in singleValueVec:
        singleRun(exePath, i, resultPath, templateName)


def readResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/default.csv"
    elapsedTime = readConfig(resultFname, "perfElapsedTime")
    memLoad = readConfig(resultFname, "memLoad")
    memStore = readConfig(resultFname, "memStore")
    instructions = readConfig(resultFname, "instructions")
    fpVector = readConfig(resultFname, "fpVector")
    fpScalar = readConfig(resultFname, "fpScalar")
    branchIns = readConfig(resultFname, "branchIns")
    return elapsedTime, memLoad, memStore, instructions, fpVector, fpScalar, branchIns


def cleanPath(path):
    os.system("sudo rm -rf " + path)
    os.system("sudo mkdir " + path)


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    memLoadVec = []
    memStoreVec = []
    instructionsVec = []
    fpVectorVec = []
    fpScalarVec = []
    branchVec = []
    for i in singleValueVec:
        elapsedTime, memLoad, memStore, instructions, fpVector, fpScalar, branchIns = (
            readResultSingle(i, resultPath)
        )
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        memLoadVec.append(float(memLoad))
        memStoreVec.append(float(memStore))
        instructionsVec.append(float(instructions))
        fpVectorVec.append(float(fpVector) / 2)
        fpScalarVec.append(float(fpScalar) / 2)
        branchVec.append(float(branchIns))
    return (
        np.array(elapseTimeVec),
        np.array(memLoadVec),
        np.array(memStoreVec),
        np.array(instructionsVec),
        np.array(fpVectorVec),
        np.array(fpScalarVec),
        np.array(branchVec),
    )


def compareMethod(exeSpace, commonPathBase, resultPaths, csvTemplates, periodVec, reRun=1):
    elapsedTimeAll = []
    memLoadAll = []
    memStoreAll = []
    periodAll = []
    instructionsAll = []
    fpVectorAll = []
    fpScalarAll = []
    branchAll = []
    for i in range(len(csvTemplates)):
        resultPath = commonPathBase + resultPaths[i]
        if reRun == 1:
            os.system("sudo rm -rf " + resultPath)
            os.system("sudo mkdir " + resultPath)
            runScanVector(exeSpace, periodVec, resultPath, csvTemplates[i])
        elapsedTime, memLoad, memStore, instructions, fpVector, fpScalar, branchIns = (
            readResultVector(periodVec, resultPath)
        )
        elapsedTimeAll.append(elapsedTime)
        memLoadAll.append(memLoad)
        memStoreAll.append(memStore)
        periodAll.append(periodVec)
        instructionsAll.append(instructions)
        fpVectorAll.append(fpVector)
        fpScalarAll.append(fpScalar)
        branchAll.append(branchIns)
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
    )


def getCyclesPerMethod(cyclesAll, valueChose):
    instructionsPerMethod = []
    for i in range(len(cyclesAll)):
        instructionsPerMethod.append(cyclesAll[int(i)][int(valueChose)])
    return np.array(instructionsPerMethod)


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    commonBase = (
        os.path.abspath(os.path.join(os.getcwd(), "../.."))
        + "/results/"
        + scanTag
        + "_instructions/"
    )
    figPath = (
        os.path.abspath(os.path.join(os.getcwd(), "../.."))
        + "/figures/"
        + scanTag
        + "_instructions"
    )
    methodTags = ["CRS", "MM"]
    resultPaths = ["crs", "mm"]
    csvTemplates = ["config_CPPCRS.csv", "config_CPPMM.csv"]
    valueVec = [200, 500, 1000, 2000, 5000]
    valueVecDisp = np.array(valueVec)
    # run
    reRun = 0
    if len(sys.argv) < 2:
        os.system("mkdir ../../results")
        os.system("mkdir ../../figures")
        os.system("mkdir " + figPath)
        os.system("sudo rm -rf " + commonBase)
        os.system("sudo mkdir " + commonBase)
        reRun = 1
    # skech
    (
        elapsedTimeAll,
        memLoadAll,
        periodAll,
        instructions,
        memStoreAll,
        fpVectorAll,
        fpScalarAll,
        branchAll,
    ) = compareMethod(exeSpace, commonBase, resultPaths, csvTemplates, valueVec, reRun)
    print(instructions, memLoadAll)
    otherIns = instructions - memLoadAll - memStoreAll - fpVectorAll - fpScalarAll - branchAll
    print(otherIns)
    # exit(-1)
    # draw2yLine("watermark time (ms)",singleValueVecDisp,lat95Vec,errVec,"95% Latency (ms)","Error","ms","",figPath+"wm_lat")
    # draw2yLine("watermark time (ms)",singleValueVecDisp,thrVec,errVec,"Throughput (KTp/s)","Error","KTp/s","",figPath+"wm_thr")
    # draw2yLine("watermark time (ms)",singleValueVecDisp,lat95Vec,compVec,"95% Latency (ms)","Completeness","ms","",figPath+"wm_omp")
    # groupLine.DrawFigureYnormal([singleValueVec,singleValueVec],[errVec,aqpErrVec],['w/o aqp',"w/ MeanAqp"],"watermark time (ms)","Error",0,1,figPath+"wm_MeanAqp",True)
    print(otherIns[0], len(otherIns))
    allowLegend = 1
    for valueChose in range(len(valueVec)):
        # instructionsPerMethod=getCyclesPerMethod(instructions,valueChose)
        memLoadPerMethod = getCyclesPerMethod(memLoadAll, valueChose)
        fpVectorPerMethod = getCyclesPerMethod(fpVectorAll, valueChose)
        fpScalarPerMethod = getCyclesPerMethod(fpScalarAll, valueChose)
        branchPerMethod = getCyclesPerMethod(branchAll, valueChose)
        otherPerMethod = getCyclesPerMethod(otherIns, valueChose)
        accuBar.DrawFigure2(
            methodTags,
            [
                memLoadPerMethod,
                memStorePerMethod,
                fpVectorPerMethod,
                fpScalarPerMethod,
                branchPerMethod,
                otherPerMethod,
            ],
            ["load", "store", "fp-vector", "fp-scalar", "branch", "others"],
            "",
            "instructions",
            figPath + "/" + scanTag + "_ins_accubar" + str(valueVecDisp[valueChose]),
            allowLegend,
            scanTag + "=" + str(valueVecDisp[valueChose]),
        )
    # print(aqpErrVec)
    # print(elapseTimeVecFD)
    # readResultsingleValue(50,resultPath)


if __name__ == "__main__":
    main()
