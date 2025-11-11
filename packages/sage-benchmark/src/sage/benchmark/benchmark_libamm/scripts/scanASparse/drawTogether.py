#!/usr/bin/env python3
import os
import sys

import accuBar as accuBar
import groupBar as groupBar
import groupBar2 as groupBar2
import groupLine as groupLine
import matplotlib
import numpy as np
from autoParase import *
from matplotlib.font_manager import FontProperties
from OoOCommon import *

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

scanTag = "aDensity"


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
    return elapsedTime, cacheMiss, cacheRefs


def cleanPath(path):
    os.system("sudo rm -rf " + path)
    os.system("sudo mkdir " + path)


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    cacheMissVec = []
    cacheRefVec = []
    for i in singleValueVec:
        elapsedTime, cacheMiss, cacheRefs = readResultSingle(i, resultPath)
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        cacheMissVec.append(float(cacheMiss))
        cacheRefVec.append(float(cacheRefs))
    return np.array(elapseTimeVec), np.array(cacheMissVec), np.array(cacheRefVec)


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    resultPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/" + scanTag
    resultPathFDAMM = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/" + scanTag + "/FDAMM"
    )
    resultPathCoFD = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/" + scanTag + "/CoFD"
    )
    resultPathBetaCoFD = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/" + scanTag + "/BCoFD"
    )
    resultPathRAWMM = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/" + scanTag + "/RAWMM"
    )
    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/" + scanTag
    configTemplate = exeSpace + "config.csv"
    valueVec = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    valueVecDisp = np.array(valueVec)
    print(configTemplate)
    # run
    if len(sys.argv) < 2:
        os.system("mkdir ../../results")
        os.system("mkdir ../../figures")
        os.system("mkdir " + figPath)
        os.system("sudo rm -rf " + resultPath)
        os.system("sudo mkdir " + resultPath)
        #
        cleanPath(resultPathFDAMM)
        cleanPath(resultPathCoFD)
        cleanPath(resultPathBetaCoFD)
        cleanPath(resultPathRAWMM)
        #
        runScanVector(exeSpace, valueVec, resultPathFDAMM, "config_FDAMM.csv")
        runScanVector(exeSpace, valueVec, resultPathCoFD, "config_CoAMM.csv")
        runScanVector(exeSpace, valueVec, resultPathBetaCoFD, "config_BCoAMM.csv")
        runScanVector(exeSpace, valueVec, resultPathRAWMM, "config_RAWMM.csv")
    evaTypes = ["FDAMM", "MM", "Co-FD", "BCO-FD"]
    elapseTimeVecFD, cacheMissVecFD, cacheRefVecFD = readResultVector(valueVec, resultPathFDAMM)
    elapseTimeVecCoFD, cacheMissVecCoFD, cacheRefVecCoFD = readResultVector(
        valueVec, resultPathCoFD
    )
    elapseTimeVeCB, cacheMissVecB, cacheRefVecB = readResultVector(valueVec, resultPathBetaCoFD)
    elapseTimeVecRAW, cacheMissVecRAW, cacheRefVecRAW = readResultVector(valueVec, resultPathRAWMM)
    # os.system("mkdir " + figPath)
    groupLine.DrawFigureXYnormal(
        [valueVec, valueVec, valueVec, valueVec],
        [elapseTimeVecFD, elapseTimeVecRAW, elapseTimeVecCoFD, elapseTimeVeCB],
        evaTypes,
        "Density of matrix A",
        "elapsed time (ms)",
        0,
        1,
        figPath + scanTag + "_elapsedTime",
        True,
    )
    groupLine.DrawFigureXYnormal(
        [valueVec, valueVec, valueVec, valueVec],
        [
            cacheMissVecFD / cacheRefVecFD * 100.0,
            cacheMissVecRAW / cacheRefVecRAW * 100.0,
            cacheMissVecCoFD / cacheRefVecCoFD * 100.0,
            cacheMissVecB / cacheRefVecB * 100.0,
        ],
        evaTypes,
        "Density of matrix A",
        "cacheMiss (%)",
        0,
        1,
        figPath + scanTag + "_cacheMiss",
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
