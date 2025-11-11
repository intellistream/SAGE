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

scanTag = "threads"


def singleRun(exePath, singleValue, resultPath, configTemplate):
    # resultFolder="singleValueTests"
    configFname = "config_" + scanTag + str(singleValue) + ".csv"
    # configTemplate = "config.csv"
    # clear old files
    os.system("cd " + exePath + "&& sudo rm *.csv")

    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    editConfig(configTemplate, exePath + configFname, scanTag, singleValue)
    # prepare new file
    # run
    os.system("cd " + exePath + "&& sudo ./benchmark " + configFname)
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
    cacheMiss = readConfig(resultFname, "cacheMiss")
    cacheRefs = readConfig(resultFname, "cacheRefs")
    froError = readConfig(resultFname, "froError")
    errorBoundRatio = readConfig(resultFname, "errorBoundRatio")
    return elapsedTime, cacheMiss, cacheRefs, froError, errorBoundRatio


def cleanPath(path):
    os.system("sudo rm -rf " + path)
    os.system("sudo mkdir " + path)


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    cacheMissVec = []
    cacheRefVec = []
    froErrorVec = []
    errorBoundRatioVec = []
    for i in singleValueVec:
        elapsedTime, cacheMiss, cacheRefs, froError, errorBoundRatio = readResultSingle(
            i, resultPath
        )
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        cacheMissVec.append(float(cacheMiss))
        cacheRefVec.append(float(cacheRefs))
        froErrorVec.append(float(froError))
        errorBoundRatioVec.append(float(errorBoundRatio))
    return (
        np.array(elapseTimeVec),
        np.array(cacheMissVec),
        np.array(cacheRefVec),
        np.array(froErrorVec),
        np.array(errorBoundRatioVec),
    )


def compareMethod(exeSpace, commonPathBase, resultPaths, csvTemplates, periodVec, reRun=1):
    elapsedTimeAll = []
    cacheMissAll = []
    cacheRefAll = []
    periodAll = []
    froAll = []
    errorBoundRatioAll = []
    for i in range(len(csvTemplates)):
        resultPath = commonPathBase + resultPaths[i]
        if reRun == 1:
            os.system("sudo rm -rf " + resultPath)
            os.system("sudo mkdir " + resultPath)
            runScanVector(exeSpace, periodVec, resultPath, csvTemplates[i])
        elapsedTime, cacheMiss, cacheRef, fro, eb = readResultVector(periodVec, resultPath)
        elapsedTimeAll.append(elapsedTime)
        cacheMissAll.append(cacheMiss)
        cacheRefAll.append(cacheRef)
        periodAll.append(periodVec)
        cacheMissRateAll = np.array(cacheMissAll) / np.array(cacheRefAll) * 100.0
        froAll.append(fro)
        errorBoundRatioAll.append(eb)
        # periodAll.append(periodVec)
    return (
        np.array(elapsedTimeAll),
        cacheMissRateAll,
        periodAll,
        np.array(froAll),
        np.array(errorBoundRatioAll),
    )


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    resultPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/" + scanTag
    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/" + scanTag + "_NOCRS"
    configTemplate = exeSpace + "config.csv"
    commonBase = resultPath + "/"
    resultPaths = ["mm", "ews", "counterSketch", "cofd", "tow"]
    csvTemplates = [
        "config_CPPMM.csv",
        "config_CPPEWS.csv",
        "config_CPPCOUNTERSKETCH.csv",
        "config_CPPCOFD.csv",
        "config_CPPTOW.csv",
    ]
    methodTags = ["mm", "ews", "counterSketch", "cofd", "tow"]
    valueVec = [1, 2, 3, 4, 5, 6, 7, 8]
    print(configTemplate)
    reRun = 0
    # run
    if len(sys.argv) < 2:
        os.system("mkdir ../../results")
        os.system("mkdir ../../figures")
        os.system("mkdir " + figPath)
        os.system("sudo rm -rf " + resultPath)
        os.system("sudo mkdir " + resultPath)
        #
        reRun = 1
        tRows = len(resultPaths)
        tCols = len(valueVec)
        elapseTimeAllSum = np.zeros((tRows, tCols))
        froErroAllSum = np.zeros((tRows, tCols))
        errorBoundRatioSum = np.zeros((tRows, tCols))
        cacheMissAll = np.zeros((tRows, tCols))
    rounds = 5
    for i in range(rounds):
        elapseTimeAll, ch, periodAll, fro, eb = compareMethod(
            exeSpace, commonBase, resultPaths, csvTemplates, valueVec, reRun
        )
        elapseTimeAllSum = elapseTimeAllSum + elapseTimeAll
        froErroAllSum = froErroAllSum + fro
        errorBoundRatioSum = errorBoundRatioSum + eb
        cacheMissAll = cacheMissAll + ch
    elapseTimeAllSum = elapseTimeAllSum / float(rounds)
    froErroAllSum = froErroAllSum / float(rounds)
    errorBoundRatioSum = errorBoundRatioSum / float(rounds)
    cacheMissAll = cacheMissAll / float(rounds)
    # evaTypes = ['FDAMM', 'MM', 'Co-FD', 'BCO-FD']

    # elapseTimeVecFD, cacheMissVecFD, cacheRefVecFD = readResultVector(valueVecRun, resultPathFDAMM)
    # elapseTimeVecCoFD, cacheMissVecCoFD, cacheRefVecCoFD = readResultVector(valueVecRun, resultPathCoFD)
    # elapseTimeVeCB, cacheMissVecB, cacheRefVecB = readResultVector(valueVecRun, resultPathBetaCoFD)

    # os.system("mkdir " + figPath)
    groupLine.DrawFigureXYnormal(
        periodAll,
        1 / elapseTimeAllSum,
        methodTags,
        "#threads",
        "1/elapsed time (1/ms)",
        0,
        1,
        figPath + "/" + "threads" + "_elapsedTime",
        True,
    )
    groupLine.DrawFigureXYnormal(
        periodAll,
        froErroAllSum * 100.0,
        methodTags,
        "#threads",
        "normalized error %",
        0,
        1,
        figPath + "/" + "threads" + "_froError",
        True,
    )
    groupLine.DrawFigureXYnormal(
        periodAll,
        errorBoundRatioSum * 100.0,
        methodTags,
        "#threads",
        "error bound ratio %",
        0,
        1,
        figPath + "/" + "threads" + "_ebRatio",
        True,
    )
    groupLine.DrawFigureXYnormal(
        periodAll,
        cacheMissAll,
        methodTags,
        "#threads",
        "cache miss %",
        0,
        1,
        figPath + "/" + "threads" + "_cachemiss",
        True,
    )
    # draw2yLine("watermark time (ms)",singleValueVecDisp,lat95Vec,errVec,"95% Latency (ms)","Error","ms","",figPath+"wm_lat")
    # draw2yLine("watermark time (ms)",singleValueVecDisp,thrVec,errVec,"Throughput (KTp/s)","Error","KTp/s","",figPath+"wm_thr")
    # draw2yLine("watermark time (ms)",singleValueVecDisp,lat95Vec,compVec,"95% Latency (ms)","Completeness","ms","",figPath+"wm_omp")
    # groupLine.DrawFigureYnormal([singleValueVec,singleValueVec],[errVec,aqpErrVec],['w/o aqp',"w/ MeanAqp"],"watermark time (ms)","Error",0,1,figPath+"wm_MeanAqp",True)
    # print(errVec)
    # print(aqpErrVec)
    # print(elapseTimeVecFD)
    # readResultsingleValue(50,resultPath)


if __name__ == "__main__":
    main()
