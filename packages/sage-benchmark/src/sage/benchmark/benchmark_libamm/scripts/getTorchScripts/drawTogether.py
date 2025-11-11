#!/usr/bin/env python3
import os

import accuBar as accuBar
import groupBar2 as groupBar2
import groupLine as groupLine
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from autoParase import *
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import LinearLocator
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

m_cifar10 = 512
n_cifar10 = 10000
l_cifar10 = 10
m_cifar100 = 512
n_cifar100 = 10000
l_cifar100 = 100


def runPeriod(
    exePath, srcA, srcB, algoTag, resultPath, configTemplate="config.csv", prefixTag="null"
):
    # (Pdb) exePath, srcA,srcB, algoTag, resultPath, configTemplate,prefixTag
    # ('/home/yuhao/Documents/work/SUTD/AMM/codespace/NEWLibAMM/LibAMM/benchmark/', 'dummy', 'dummy', 'int8', '/home/yuhao/Documents/work/SUTD/AMM/codespace/NEWLibAMM/LibAMM/benchmark/results/Downstream_Inference_static_lazy/int8', 'config_dnn_inference.csv', 'cifar10')
    os.system("sudo rm -rf " + resultPath + "/" + str(prefixTag))
    os.system("sudo mkdir " + resultPath + "/" + str(prefixTag))
    os.system("sudo chmod 777 " + resultPath + "/" + str(prefixTag))
    # resultFolder="periodTests"
    configFname = "config_period_" + prefixTag + ".csv"
    configTemplate = "config_dnn_inference.csv"
    # clear old files
    os.system("cd " + exePath + "&& sudo rm *.csv")
    os.system("cp perfListEvaluation.csv " + exePath)

    editConfig(
        configTemplate, exePath + "temp1.csv", "sketchDimension", int(16 * 16 / 10000 * 512)
    )  # num of subspace * ncodebook / num of rows * num of cols
    editConfig(exePath + "temp1.csv", exePath + "temp2.csv", "cppAlgoTag", algoTag)

    # blockLRA rank ratio
    editConfig(
        exePath + "temp2.csv", exePath + "temp1.csv", "algoARankRatio", 16 * 16 / 10000
    )  # num of subspace * ncodebook / num of rows
    editConfig(exePath + "temp1.csv", exePath + "temp2.csv", "algoBRankRatio", 16 * 16 / 10000)

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
            f"{pqvqCodewordLookUpTableDir}/{prefixTag}_train_m1_*"
        )[0]
    elif algoTag == "pq":
        pqvqCodewordLookUpTablePath = glob.glob(
            f"{pqvqCodewordLookUpTableDir}/{prefixTag}_train_m10_*"
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
    from os.path import join

    command = f"export OMP_NUM_THREADS=1 && \
        cd {join(exePath, 'scripts/Downstream_Inference/bolt/experiments')} && \
        python3 -m python.amm_main \
            --task {prefixTag} \
            --config_load_path {join(exePath, configFname)} \
            --metric_save_path {join(resultPath, prefixTag, 'DNNInferenceMetrics.csv')}"
    # command = f"export OMP_NUM_THREADS=1 && \
    #     cd {join(exePath, 'scripts/Downstream_Inference/bolt/experiments')} && \
    #     python3 -m python.amm_main \
    #         --task {prefixTag} \
    #         --config_load_path {join(exePath, configFname)} \
    #         --metric_save_path {join(resultPath, prefixTag, 'DNNInferenceMetrics.csv')}"

    os.system(command)

    os.system(
        "cd " + exePath + "&& sudo cp *.csv execution_log.txt " + resultPath + "/" + str(prefixTag)
    )
    # copy result


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
    resultFname = resultPath + "/" + str(singleValue) + "/DNNInferenceMetrics.csv"
    elapsedTime = readConfig(resultFname, "AMMPerfElapsedTime")
    froError = readConfig(resultFname, "AMMFroError")
    errorBoundRatio = 100
    thr = readConfig(resultFname, "AMMThroughput")
    endingAcc = readConfig(resultFname, "acc_amm")
    return elapsedTime, froError, errorBoundRatio, thr, endingAcc


def tryTorchScripts(exePath):
    tryDownload = 0
    tsPath = exePath + "/torchscripts"
    print(tsPath)
    fileId = " https://www.dropbox.com/scl/fi/obfvtxrdcrjksfqbqegsz/torchscripts.tar?rlkey=bb27zgxuzgwg8vechir0k4f64"
    downloadCmd = "cd " + exePath + "&& wget -O torchscripts.tar " + fileId
    if os.path.exists(tsPath):
        return 1
    while tryDownload < 10:
        os.system(downloadCmd)
        os.system("cd " + exePath + "&&tar -xf torchscripts.tar")

        if os.path.exists(tsPath):
            return 1
        tryDownload = tryDownload + 1
    return 0


def checkDependecies(exePath):
    if os.path.exists(exePath + "amm_torchscripts"):
        print("dependecy installed, skip")
        return
    if tryTorchScripts(exePath):
        print("torchscipt is done")
    else:
        print("error in gettingb ts")
    # 0 get bolt
    # os.system('wget https://www.dropbox.com/scl/fi/94q58vbbhgeij0kvamwmx/bolt.tar?rlkey=vnjhl92rlz7vrnf2jf440dyi4')
    # os.system('tar -xf bolt.tar?rlkey=vnjhl92rlz7vrnf2jf440dyi4')
    os.system("touch " + exePath + "amm_torchscripts")
    print("install deps done")


def checkResultSingle(singleValue, resultPath):
    resultFname = resultPath + "/" + str(singleValue) + "/DNNInferenceMetrics.csv"
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
    endingAccVec = []
    for i in singleValueVec:
        elapsedTime, froError, errorBoundRatio, thr, endingAcc = readResultSingle(i, resultPath)
        elapseTimeVec.append(float(elapsedTime) / 1000.0)
        froErrorVec.append(float(froError))
        errorBoundRatioVec.append(float(errorBoundRatio))
        thrVec.append(float(thr))
        endingAccVec.append(float(endingAcc))
    return (
        np.array(elapseTimeVec),
        np.array(froErrorVec),
        np.array(errorBoundRatioVec),
        np.array(thrVec),
        np.array(endingAccVec),
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
    endingAccAll = []
    resultIsComplete = 1
    for i in range(len(algos)):
        resultPath = commonPathBase + resultPaths[i]
        algoTag = algos[i]
        os.system("sudo mkdir " + resultPath)
        os.system("sudo chmod 777 " + resultPath)
        if reRun == 1:
            os.system("sudo rm -rf " + resultPath)
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
                    runPeriodVector(
                        exeSpace, srcAVec, srcBVec, algoTag, resultPath, dataSetName, csvTemplate, 2
                    )
                    resultIsComplete = checkResultVector(dataSetName, resultPath)

        if resultIsComplete:
            # exit()
            elapsedTime, fro, eb, thr, endingAcc = readResultVector(dataSetName, resultPath)
            elapsedTimeAll.append(elapsedTime)
            periodAll.append(dataSetName)
            froAll.append(fro)
            errorBoundRatioAll.append(eb)
            thrAll.append(thr)
            endingAccAll.append(endingAcc)
    return (
        np.array(elapsedTimeAll),
        np.array(froAll),
        np.array(errorBoundRatioAll),
        np.array(thrAll),
        periodAll,
        np.array(endingAccAll),
    )


def draw2yBar(NAME, R1, R2, l1, l2, fname):
    fig, ax1 = plt.subplots(figsize=(10, 4))
    width = 0.2  # 柱形的宽度
    x1_list = []
    x2_list = []
    bars = []
    index = np.arange(len(NAME))
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
        os.path.abspath(os.path.join(os.getcwd(), "../.."))
        + "/results/Downstream_Inference_static_lazy/"
    )

    figPath = (
        os.path.abspath(os.path.join(os.getcwd(), "../.."))
        + "/figures/Downstream_Inference_static_lazy/"
    )
    checkDependecies(exeSpace)
    exit()

    #                      5, 15, figPath + "sec4_1_cca_static_lazy_throughput_log", True)


if __name__ == "__main__":
    main()
