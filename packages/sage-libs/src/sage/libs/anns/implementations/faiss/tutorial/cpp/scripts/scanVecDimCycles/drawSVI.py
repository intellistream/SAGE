#!/usr/bin/env python3
import csv
import numpy as np
import matplotlib.pyplot as plt
import accuBar as accuBar
import groupBar as groupBar
import groupBar2 as groupBar2
import groupLine as groupLine
from autoParase import *
import itertools as it
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pylab
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import LogLocator, LinearLocator
import os
import pandas as pd
import sys
from OoOCommon import *

OPT_FONT_NAME = 'Helvetica'
TICK_FONT_SIZE = 22
LABEL_FONT_SIZE = 28
LEGEND_FONT_SIZE = 30
LABEL_FP = FontProperties(style='normal', size=LABEL_FONT_SIZE)
LEGEND_FP = FontProperties(style='normal', size=LEGEND_FONT_SIZE)
TICK_FP = FontProperties(style='normal', size=TICK_FONT_SIZE)

MARKERS = (['*', '|', 'v', "^", "", "h", "<", ">", "+", "d", "<", "|", "", "+", "_"])
# you may want to change the color map for different figures
COLOR_MAP = (
    '#B03A2E', '#2874A6', '#239B56', '#7D3C98', '#FFFFFF', '#F1C40F', '#F5CBA7', '#82E0AA', '#AEB6BF', '#AA4499')
# you may want to change the patterns for different figures
PATTERNS = (["////", "o", "", "||", "-", "//", "\\", "o", "O", "////", ".", "|||", "o", "---", "+", "\\\\", "*"])
LABEL_WEIGHT = 'bold'
LINE_COLORS = COLOR_MAP
LINE_WIDTH = 3.0
MARKER_SIZE = 15.0
MARKER_FREQUENCY = 1000

matplotlib.rcParams['ps.useafm'] = True
matplotlib.rcParams['pdf.use14corefonts'] = True
matplotlib.rcParams['xtick.labelsize'] = TICK_FONT_SIZE
matplotlib.rcParams['ytick.labelsize'] = TICK_FONT_SIZE
matplotlib.rcParams['font.family'] = OPT_FONT_NAME
matplotlib.rcParams['pdf.fonttype'] = 42


def runPeriod(exePath, period, resultPath, configTemplate="config.csv"):
    # resultFolder="periodTests"
    configFname = "config_period_" + str(period) + ".csv"
    # configTemplate = "config.csv"
    # clear old files
    os.system("cd " + exePath + "&& rm *.csv")

    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    editConfig(configTemplate, exePath + configFname, "watermarkTimeMs", period)
    # prepare new file
    # run
    os.system("cd " + exePath + "&& ./benchmark " + configFname)
    # copy result
    os.system("rm -rf " + resultPath + "/" + str(period))
    os.system("mkdir " + resultPath + "/" + str(period))
    os.system("cd " + exePath + "&& cp *.csv " + resultPath + "/" + str(period))


def runPeriodVector(exePath, periodVec, resultPath, configTemplate="config.csv"):
    for i in periodVec:
        runPeriod(exePath, i, resultPath, configTemplate)


def readResultPeriod(period, resultPath):
    resultFname = resultPath + "/" + str(period) + "/default_general.csv"
    avgLat = readConfig(resultFname, "AvgLatency")
    lat95 = readConfig(resultFname, "95%Latency")
    thr = readConfig(resultFname, "Throughput")
    err = readConfig(resultFname, "AQPError")
    return avgLat, lat95, thr, err


def readResultVectorPeriod(periodVec, resultPath):
    avgLatVec = []
    lat95Vec = []
    thrVec = []
    errVec = []
    compVec = []
    for i in periodVec:
        avgLat, lat95, thr, err = readResultPeriod(i, resultPath)
        avgLatVec.append(float(avgLat) / 1000.0)
        lat95Vec.append(float(lat95) / 1000.0)
        thrVec.append(float(thr) / 1000.0)
        errVec.append(abs(float(err)))
        compVec.append(1 - abs(float(err)))
    return avgLatVec, lat95Vec, thrVec, errVec, compVec


def compareMethod(exeSpace, commonPathBase, resultPaths, csvTemplates, periodVec, reRun=1):
    lat95All = []
    errAll = []
    periodAll = []
    for i in range(len(csvTemplates)):
        resultPath = commonPathBase + resultPaths[i]
        if (reRun == 1):
            os.system("rm -rf " + resultPath)
            os.system("mkdir " + resultPath)
            runPeriodVector(exeSpace, periodVec, resultPath, csvTemplates[i])
        avgLatVec, lat95Vec, thrVec, errVec, compVec = readResultVectorPeriod(periodVec, resultPath)
        lat95All.append(lat95Vec)
        errAll.append(errVec)
        periodAll.append(periodVec)
    return lat95All, errAll, periodAll


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    commonBasePath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/figE2E/"

    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/"
    configTemplate = exeSpace + "config.csv"
    periodVec = [7, 8, 9, 10, 11, 12]
    periodVecDisp = np.array(periodVec)
    periodVecDisp = periodVecDisp
    print(configTemplate)

    reRun = 0
    if (len(sys.argv) < 2):
        os.system("rm -rf " + commonBasePath)
        os.system("mkdir " + commonBasePath)
        reRun = 1
        # runPeriodVector(exeSpace, periodVec, resultPath)
    # os.system("mkdir " + figPath)
    # print(lat95All)
    # print(lat95All)
    # lat95All[3]=ts
    methodTags = ["WMJ", "PECJ-alf", "(PECJ-vae)/7.5", "svi"]
    resultPaths = ["wa", "pecj_ks", "pec_ai", "svi"]
    csvTemplates = ["config_waterMark.csv", "config_ima.csv", "config_pecjAI.csv", "config_svi.csv"]
    lat95All, errAll, periodAll = compareMethod(exeSpace, commonBasePath, resultPaths, csvTemplates, periodVec, reRun)
    npLat = np.array(lat95All)
    npLat[2] = npLat[2] / 7.5
    groupLine.DrawFigure2(npLat, errAll, methodTags, "95% latency (ms)", "Error", 0, 1, figPath + "svie2ESmall", True)


if __name__ == "__main__":
    main()
