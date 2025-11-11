#!/usr/bin/env python3
# pragma: allowlist secret
import math
import os
import sys

import accuBar as accuBar
import groupBar2 as groupBar2
import groupLine as groupLine
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import LinearLocator
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

m_mediamill = 43907
n_mediamill = 120
l_mediamill = 101
m_mnist = 60000
n_mnist = 392
l_mnist = 392
epsilon = 0.5
delta = 0.2

dataset_sketchAcols_mapping = {
    "MediaMill": min(
        int(
            epsilon ** (-2)
            * (math.sqrt(n_mediamill + l_mediamill) + math.sqrt(math.log(m_mediamill / delta))) ** 2
            * math.log(n_mediamill + l_mediamill)
            / delta
        ),
        m_mediamill,
    ),
    "MNIST": min(
        int(
            epsilon ** (-2)
            * (math.sqrt(n_mnist + l_mnist) + math.sqrt(math.log(m_mnist / delta))) ** 2
            * math.log(n_mnist + l_mnist)
            / delta
        ),
        m_mnist,
    ),
}

dataset_Acols_mapping = {"MediaMill": m_mediamill, "MNIST": m_mnist}

dataset_acols_mapping = {
    "SIFT10K": 10000,
    "SIFT1M": 1000000,
    "GIST1M": 1000000,
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
    # (Pdb) exePath, srcA,srcB, algoTag, resultPath, configTemplate,prefixTag
    # ('/home/yuhao/Documents/work/SUTD/AMM/codespace/LibAMM/benchmark/', 'dummy', 'dummy', 'int8', '/home/yuhao/Documents/work/SUTD/AMM/codespace/LibAMM/benchmark/results/DownstreamCCA_static_lazy/int8', 'config_cca_static_lazy.csv', 'MediaMill')

    # resultFolder="periodTests"
    configFname = "config_period_" + prefixTag + ".csv"
    configTemplate = "config_cca_static_lazy.csv"
    # clear old files
    os.system("cd " + exePath + "&& sudo rm *.csv")
    os.system("cp perfListEvaluation.csv " + exePath)
    # editConfig(configTemplate, exePath + configFname, "earlierEmitMs", 0)
    if prefixTag == "MediaMill":
        filePath = "datasets/MediaMill/MediaMill.pth"
    elif prefixTag == "MNIST":
        filePath = "datasets/MNIST/train-images.idx3-ubyte"
    else:
        filePath = "datasets/MediaMill/MediaMill.pth"

    editConfig(configTemplate, exePath + "temp0.csv", "filePath", filePath)
    editConfig(exePath + "temp0.csv", exePath + "temp1.csv", "srcA", srcA)
    editConfig(exePath + "temp1.csv", exePath + "temp2.csv", "srcB", srcB)
    editConfig(
        exePath + "temp2.csv",
        exePath + "temp1.csv",
        "sketchDimension",
        int(dataset_acols_mapping[prefixTag] * 0.1),
    )
    editConfig(
        exePath + "temp1.csv", exePath + "temp2.csv", "cppAlgoTag", algoTag
    )  # pragma: allowlist secret

    # blockLRA rank ratio
    # editConfig(exePath+"temp2.csv", exePath+"temp1.csv", "algoARankRatio", dataset_sketchAcols_mapping[prefixTag]/dataset_Acols_mapping[prefixTag])
    # editConfig(exePath+"temp1.csv",exePath+"temp2.csv", "algoBRankRatio", dataset_sketchAcols_mapping[prefixTag]/dataset_Acols_mapping[prefixTag])

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
        pqvqCodewordLookUpTablePath = glob.glob(
            f"{pqvqCodewordLookUpTableDir}/{prefixTag}_AA_m1_*"
        )[0]
    elif algoTag == "pq":
        pqvqCodewordLookUpTablePath = glob.glob(
            f"{pqvqCodewordLookUpTableDir}/{prefixTag}_AA_m10_*"
        )[0]
    editConfig(
        exePath + "temp1.csv",
        exePath + configFname,
        "pqvqCodewordLookUpTablePath",
        pqvqCodewordLookUpTablePath,
    )

    # clean dir

    # prepare new file
    # run
    os.system(
        "export OMP_NUM_THREADS=1 &&" + "cd " + exePath + "&& sudo ./benchmarkCCA " + configFname
    )
    os.system("sudo rm -rf " + resultPath + "/" + str(prefixTag))
    os.system("sudo mkdir " + resultPath + "/" + str(prefixTag))
    # copy result
    os.system(
        "cd " + exePath + "&& sudo cp *.csv execution_log.txt " + resultPath + "/" + str(prefixTag)
    )


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
    resultFname = resultPath + "/" + str(singleValue) + "/CCA.csv"
    elapsedTime = readConfig(resultFname, "AMMPerfElapsedTime")
    froError = readConfig(resultFname, "SxxFroError")
    errorBoundRatio = 100
    thr = readConfig(resultFname, "AMMThroughput")
    endingError = readConfig(resultFname, "CorrelationError")
    return elapsedTime, froError, errorBoundRatio, thr, endingError


def checkResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/CCA.csv"
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


def readResultVector(singleValueVec, resultPath):
    elapseTimeVec = []
    froErrorVec = []
    errorBoundRatioVec = []
    thrVec = []
    endingErrorVec = []
    for i in singleValueVec:
        elapsedTime, froError, errorBoundRatio, thr, endingError = readResultSingle(i, resultPath)
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        froErrorVec.append(float(froError))
        errorBoundRatioVec.append(float(errorBoundRatio))
        thrVec.append(float(thr))
        endingErrorVec.append(float(endingError))
    return (
        np.array(elapseTimeVec),
        np.array(froErrorVec),
        np.array(errorBoundRatioVec),
        np.array(thrVec),
        np.array(endingErrorVec),
    )


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
    periodAll = []
    froAll = []
    errorBoundRatioAll = []
    thrAll = []
    endingErrorAll = []
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
                    os.system("sudo mkdir " + resultPath)
                    runPeriodVector(
                        exeSpace, srcAVec, srcBVec, algoTag, resultPath, dataSetName, csvTemplate, 2
                    )
                    resultIsComplete = checkResultVector(dataSetName, resultPath)

        if resultIsComplete:
            # exit()
            elapsedTime, fro, eb, thr, endingError = readResultVector(dataSetName, resultPath)
            elapsedTimeAll.append(elapsedTime)
            periodAll.append(dataSetName)
            froAll.append(fro)
            errorBoundRatioAll.append(eb)
            thrAll.append(thr)
            endingErrorAll.append(endingError)
    return (
        np.array(elapsedTimeAll),
        np.array(froAll),
        np.array(errorBoundRatioAll),
        np.array(thrAll),
        periodAll,
        np.array(endingErrorAll),
    )


def draw2yBar(NAME, R1, R2, l1, l2, fname):
    fig, ax1 = plt.subplots(figsize=(10, 4))
    width = 0.2  # 柱形的宽度
    x1_list = []
    x2_list = []
    bars = []
    for i in range(len(R1)):
        x1_list.append(i)
        x2_list.append(i + width)
    # ax1.set_ylim(0, 1)
    bars.append(
        ax1.bar(
            x1_list,
            R1,
            width=width,
            color=COLOR_MAP[0],
            hatch=PATTERNS[0],
            align="edge",
            edgecolor="black",
            linewidth=3,
        )
    )
    ax1.set_ylabel("ms", fontproperties=LABEL_FP)
    ax1.set_xticklabels(ax1.get_xticklabels())  # 设置共用的x轴
    ax2 = ax1.twinx()

    # ax2.set_ylabel('latency/us')
    # ax2.set_ylim(0, 0.5)
    bars.append(
        ax2.bar(
            x2_list,
            R2,
            width=width,
            color=COLOR_MAP[1],
            hatch=PATTERNS[1],
            align="edge",
            tick_label=NAME,
            edgecolor="black",
            linewidth=3,
        )
    )

    ax2.set_ylabel("%", fontproperties=LABEL_FP)
    # plt.grid(axis='y', color='gray')

    # style = dict(size=10, color='black')
    # ax2.hlines(tset, 0, x2_list[len(x2_list)-1]+width, colors = "r", linestyles = "dashed",label="tset")
    # ax2.text(4, tset, "$T_{set}$="+str(tset)+"us", ha='right', **style)
    if 1:
        plt.legend(
            bars,
            [l1, l2],
            prop=LEGEND_FP,
            ncol=2,
            loc="upper center",
            #                     mode='expand',
            shadow=False,
            bbox_to_anchor=(0.55, 1.45),
            columnspacing=0.1,
            handletextpad=0.2,
            borderaxespad=-1,
            #                     bbox_transform=ax.transAxes,
            #                     frameon=True,
            #                     columnspacing=5.5,
            #                     handlelength=2,
        )
    plt.xlabel(NAME, fontproperties=LABEL_FP)
    plt.xticks(size=TICK_FONT_SIZE)
    ax1.yaxis.set_major_locator(LinearLocator(5))
    ax2.yaxis.set_major_locator(LinearLocator(5))
    ax1.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f"))
    ax2.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f"))
    plt.tight_layout()
    plt.savefig(fname + ".pdf")


def main():
    exeSpace = os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/"
    commonBasePath = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/DownstreamCCA_static_lazy/"
    )

    figPath = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/figures/DownstreamCCA_static_lazy/"
    )

    # add the datasets here
    # srcAVec=["datasets/AST/mcfe.mtx"] # 765*756
    # srcBVec=["datasets/AST/mcfe.mtx"] # 765*756
    # dataSetNames=['AST']
    # srcAVec=['datasets/UTM/utm1700a.mtx'] # 1700*1700
    # srcBVec=['datasets/UTM/utm1700b.mtx'] # 1700*1700
    # dataSetNames=['UTM']
    # srcAVec=['dummy']
    # srcBVec=['dummy']
    # dataSetNames=['MediaMill']
    srcAVec = ["datasets/RDB/rdb2048.mtx"]
    srcBVec = ["datasets/RDB/rdb2048l.mtx"]
    dataSetNames = ["RDB"]
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
    # add the algo tag here
    # algosVec=['crs', 'mm']
    # algoDisp=['CRS', 'LTMM']
    # add the algo tag here
    # algosVec=['crs', 'fastjlt']
    # algoDisp=['CRS', 'FastJLT']
    # algosVec=['int8_fp32', 'mm']
    # algoDisp=['NLMM', 'LTMM']
    # algosVec=['tugOfWar']
    # algoDisp=['TugOfWar']
    # algosVec=['blockLRA', 'vq', 'pq', 'rip', 'smp-pca', 'weighted-cr', 'tugOfWar', 'int8_fp32', 'mm']
    # algosVec=['int8', 'crs', 'countSketch', 'cooFD', 'blockLRA', 'fastjlt', 'vq', 'pq', 'rip', 'smp-pca', 'weighted-cr', 'tugOfWar', 'int8_fp32', 'mm']
    # algoDisp=['INT8', 'CRS', 'CS', 'CoOFD', 'BlockLRA', 'FastJLT', 'VQ', 'PQ', 'RIP', 'SMP-PCA', 'WeightedCR', 'TugOfWar',  'NLMM', 'LTMM']
    # algoDisp=['BlockLRA', 'VQ', 'PQ', 'RIP', 'SMP-PCA', 'WeightedCR', 'TugOfWar',  'NLMM', 'LTMM']
    # algosVec=['rip']#, 'smp-pca', 'weighted-cr', 'tugOfWar', 'int8_fp32', 'mm']
    # algoDisp=['RIP']#, 'SMP-PCA', 'WeightedCR', 'TugOfWar',  'NLMM', 'LTMM']

    # algosVec=['int8', 'crs', 'countSketch', 'cooFD', 'blockLRA', 'fastjlt', 'vq', 'pq', 'rip', 'smp-pca', 'weighted-cr', 'tugOfWar', 'int8_fp32', 'mm']
    # algoDisp=['INT8', 'CRS', 'CS', 'CoOFD', 'BlockLRA', 'FastJLT', 'VQ', 'PQ', 'RIP', 'SMP-PCA', 'WeightedCR', 'TugOfWar',  'NLMM', 'LTMM']

    # add the algo tag here
    # algosVec=['int8', 'weighted-cr', 'vq', 'int8_fp32']
    # this template configs all algos as lazy mode, all datasets are static and normalized
    csvTemplate = "config_cca_static_lazy.csv"
    # do not change the following
    resultPaths = algosVec
    os.system("mkdir ../../results")
    os.system("mkdir ../../figures")
    os.system("mkdir " + figPath)
    # run
    reRun = 2
    os.system("sudo mkdir " + commonBasePath)
    if len(sys.argv) < 2:
        os.system("sudo rm -rf " + commonBasePath)

        reRun = 1
    elapsedTimeAll, errAll, ebAll, thrAll, periodAll, endingErrorAll = compareMethod(
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

    errAll = np.array(errAll) * 100.0
    endingErrorAll = np.array(endingErrorAll) * 100.0
    elapsedTimeAll = np.array(elapsedTimeAll)
    thrAll = np.array(thrAll) / 1000.0

    # int8 = int8 / int8_fp32 * mm
    # elapsedTimeAll[0] = elapsedTimeAll[0]/elapsedTimeAll[-2]*elapsedTimeAll[-1]
    # thrAll[0] = thrAll[0]/thrAll[-2]*thrAll[-1]

    # draw2yBar(methodTags,[elapsedTimeAll[0][0],elapsedTimeAll[1][0],elapsedTimeAll[2][0],elapsedTimeAll[3][0]],[errAll[0][0],errAll[1][0],errAll[2][0],errAll[3][0]],'95% latency (ms)','Error (%)',figPath + "sec6_5_stock_q1_normal")
    groupBar2.DrawFigure2(
        dataSetNames,
        errAll,
        methodTags,
        "Datasets",
        "Error (%)",
        5,
        15,
        figPath + "sec4_1_cca_static_lazy_fro",
        True,
    )
    groupBar2.DrawFigure2(
        dataSetNames,
        endingErrorAll,
        methodTags,
        "Datasets",
        "Error (%)",
        5,
        15,
        figPath + "sec4_1_cca_static_lazy_ending_error",
        True,
    )
    groupBar2.DrawFigure2(
        dataSetNames,
        np.log(elapsedTimeAll),
        methodTags,
        "Datasets",
        "95% latency (ms)",
        5,
        15,
        figPath + "sec4_1_cca_static_lazy_latency_log",
        True,
    )
    print(elapsedTimeAll)
    return elapsedTimeAll, errAll, endingErrorAll
    # groupBar2.DrawFigure2(dataSetNames, np.log(thrAll), methodTags, "Datasets", "elements/ms",
    #                      5, 15, figPath + "sec4_1_cca_static_lazy_throughput_log", True)


if __name__ == "__main__":
    main()
