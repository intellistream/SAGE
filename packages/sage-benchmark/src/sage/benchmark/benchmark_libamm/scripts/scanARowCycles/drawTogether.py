#!/usr/bin/env python3
import os
import sys

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
    editConfig(configTemplate, exePath + "temp1.csv", "aRow", prefixTag)
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
        pqvqCodewordLookUpTablePath = glob.glob(
            f"{pqvqCodewordLookUpTableDir}/rows_{prefixTag}_m1*"
        )[0]
    elif algoTag == "pq":
        # pqvqCodewordLookUpTablePath = glob.glob(f'{pqvqCodewordLookUpTableDir}/{prefixTag}_m10_row*')[0]
        pqvqCodewordLookUpTablePath = glob.glob(
            f"{pqvqCodewordLookUpTableDir}/rows_{prefixTag}_m1*"
        )[0]
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
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/scanARowCycles/"
    )

    figPath = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/scanARowCycles"

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
    # aRowVec= [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
    aRowVec = [100, 500, 1000, 2500, 5000, 10000, 25000, 50000]
    # aRowVec=[100, 200, 500, 1000]
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
    # algosVec=[ 'pq']
    # algoDisp=['PQ']
    # add the algo tag here

    # this template configs all algos as lazy mode, all datasets are static and normalized
    csvTemplate = "config_e2e_static_lazy.csv"
    # do not change the following
    resultPaths = algosVec
    os.system("mkdir ../../results")
    os.system("mkdir ../../figures")
    os.system("mkdir " + figPath)
    # run
    reRun = 0
    if len(sys.argv) < 2:
        os.system("sudo rm -rf " + commonBasePath)

        reRun = 1
    else:
        reRun = int(sys.argv[1])
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
    ) = compareMethod(exeSpace, commonBasePath, resultPaths, csvTemplate, algosVec, aRowVec, reRun)
    # Add some pre-process logic for int8 here if it is used
    for instruc in [
        instructions,
        cpuCycleAll,
        memStallAll,
        l1dStallAll,
        l2StallAll,
        l3StallAll,
        totalStallAll,
    ]:
        instruc = np.maximum(instruc, 0)
        int8_adjust_ratio = instruc[0] / instruc[-2]
        instruc[0] = instruc[-1] * int8_adjust_ratio
    otherStallsAll = totalStallAll - memStallAll - l1dStallAll - l2StallAll - l3StallAll
    otherStallsAll = np.maximum(otherStallsAll, 0)
    totalStallAll = memStallAll + l1dStallAll + l2StallAll + l3StallAll + otherStallsAll
    nonStallAll = cpuCycleAll - totalStallAll
    nonStallAll = np.maximum(nonStallAll, 0)
    cpuCycleAll = totalStallAll + nonStallAll

    int8_adjust_ratio = elapsedTimeAll[0] / elapsedTimeAll[-2]
    elapsedTimeAll[0] = elapsedTimeAll[-1] * int8_adjust_ratio
    int8_adjust_ratio = memStallAll[0] / memStallAll[-2]
    memStallAll[0] = memStallAll[-1] * int8_adjust_ratio
    # groupBar2.DrawFigureYLog(aRowVec, instructions/instructions[-1], methodTags, "Datasets", "Ins (times of LTMM)", 5, 15, figPath + "/" + "instructions", True)
    # groupBar2.DrawFigureYLog(aRowVec, fpInsAll/fpInsAll[-1], methodTags, "Datasets", "FP Ins (times of LTMM)", 5, 15, figPath + "/" + "FP_instructions", True)
    # groupBar2.DrawFigureYLog(aRowVec, memInsAll/memInsAll[-1], methodTags, "Datasets", "Mem Ins (times of LTMM)", 5, 15, figPath + "/" + "mem_instructions", True)
    # groupBar2.DrawFigure2(aRowVec, ratioFpIns, methodTags, "Datasets", "SIMD Utilization (%)", 5, 15, figPath + "/" + "SIMD utilization", True)
    # groupBar2.DrawFigure2(aRowVec, instructions/(memLoadAll+memStoreAll), methodTags, "Datasets", "IPM", 5, 15, figPath + "/" + "IPM", True)
    # groupBar2.DrawFigure2(aRowVec, fpInsAll/(memLoadAll+memStoreAll), methodTags, "Datasets", "FP Ins per Unit Mem Access", 5, 15, figPath + "/" + "FPIPM", True)
    # groupBar2.DrawFigure2(aRowVec, (memLoadAll+memStoreAll)/(instructions)*100.0, methodTags, "Datasets", "Ratio of Mem Ins (%)", 5, 15, figPath + "/" + "mem", True)

    # groupBar2.DrawFigure2(aRowVec, branchAll/instructions*100.0, methodTags, "Datasets", "Ratio of Branch Ins (%)", 5, 15, figPath + "/" + "branches", True)
    # groupBar2.DrawFigure2(aRowVec, otherIns/instructions*100.0, methodTags, "Datasets", "Ratio of Other Ins (%)", 5, 15, figPath + "/" + "others", True)
    # print(instructions[-1],instructions[2])

    # groupBar2.DrawFigure2(dataSetNames, np.log(thrAll), methodTags, "Datasets", "elements/ms", 5, 15, figPath + "sec4_1_e2e_static_lazy_throughput_log", True)
    groupLine.DrawFigureYLog(
        periodAll,
        elapsedTimeAll,
        methodTags,
        "#Rows of A",
        r"Processing Latency l (ms)",
        0,
        1,
        figPath + "/" + "aRows_lat",
        True,
    )
    groupLine.DrawFigureYLog(
        periodAll,
        memStallAll,
        methodTags,
        "#Rows of A",
        r"Memot Stall Cycles",
        0,
        1,
        figPath + "/" + "aRows_memStall",
        False,
    )
    groupLine.DrawFigureYnormal(
        periodAll,
        froAll,
        methodTags,
        "#Rows of A",
        r"AMM Error $\epsilon$ ",
        0,
        1,
        figPath + "/" + "aRows_err",
        False,
    )
    print(elapsedTimeAll)


if __name__ == "__main__":
    main()
