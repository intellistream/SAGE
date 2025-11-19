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

scanTag = "algoDelta"


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
    os.system("cd " + exePath + "&& sudo env OMP_NUM_THREADS=1 ./benchmark " + configFname)
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
    commonBase = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/" + scanTag + "/"
    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/" + scanTag
    methodTags = ["TOW", "MM"]
    resultPaths = ["tow", "mm"]
    csvTemplates = ["config_CPPTOW.csv", "config_RAWMM.csv"]
    valueVec = [0.2, 0.1, 0.02, 0.005, 5e-4, 2e-9, 9e-14, 2e-22, 3e-44]
    np.array(valueVec)
    # run
    reRun = 0
    if len(sys.argv) < 2:
        os.system("mkdir ../../results")
        os.system("mkdir ../../figures")
        os.system("mkdir " + figPath)
        os.system("sudo rm -rf " + commonBase)
        os.system("sudo mkdir " + commonBase)
        reRun = 1

    elapsedTimeAll, cacheMissAll, periodAll, fro, eb = compareMethod(
        exeSpace, commonBase, resultPaths, csvTemplates, valueVec, reRun
    )
    groupLine.DrawFigure2(
        periodAll,
        elapsedTimeAll,
        methodTags,
        "value of delta",
        "elapsed time (ms)",
        0,
        1,
        figPath + "/" + scanTag + "_elapsedTime",
        True,
    )
    groupLine.DrawFigureYnormal(
        periodAll,
        cacheMissAll,
        methodTags,
        "value of delta",
        "cacheMiss (%)",
        0,
        1,
        figPath + "/" + scanTag + "_cacheMiss",
        True,
    )

    groupLine.DrawFigureYnormal(
        periodAll,
        fro * 100.0,
        methodTags,
        "value of delta",
        "normalized error %",
        0,
        1,
        figPath + "/" + scanTag + "_froError",
        True,
    )
    groupLine.DrawFigureYnormal(
        periodAll,
        eb * 100.0,
        methodTags,
        "value of delta",
        "error bound ratio %",
        0,
        1,
        figPath + "/" + scanTag + "_ebRatio",
        True,
    )


if __name__ == "__main__":
    main()
