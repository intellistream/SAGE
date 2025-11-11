#!/usr/bin/env python3
import os
import re
import sys

import run as run
import torch


def runAll(commonBasePath, h=500):
    original_stdout = sys.stdout
    algosVec = [
        "int8",
        "crs",
        "countSketch",
        "cooFD",
        "blockLRA",
        "fastjlt",
        "rip",
        "smp-pca",
        "weighted-cr",
        "tugOfWar",
        "int8_fp32",
        "mm",
    ]
    (
        os.path.abspath(os.path.join(os.getcwd(), "approx_mul_pytorch/functional"))
        + "/approx_linear.py"
    )
    for hidden in [500, 2000]:
        for i in range(len(algosVec)):
            algo = algosVec[i]
            resultPath = commonBasePath + "/" + algo + str(hidden)
            if os.path.exists(resultPath):
                continue
            # modify_file(filePath, algo)
            print("Running: " + algo)
            with open(resultPath, "w") as f:
                sys.stdout = f
                run.main(algo, hidden)
                sys.stdout = original_stdout


def extract_info(file_path):
    with open(file_path) as file:
        content = file.read()

    # Regular expression to find the time in the line with "19:"
    time_pattern = r"19：\(wall time: ([\d.]+) sec\)"
    time_match = re.search(time_pattern, content)
    time_19 = time_match.group(1) if time_match else 0

    # Regular expression to find the accuracy in the line with "test acc:"
    accuracy_pattern = r"test acc: ([\d.]+)"
    accuracy_match = re.search(accuracy_pattern, content)
    test_accuracy = accuracy_match.group(1) if accuracy_match else 0

    return time_19, test_accuracy


def parseResult(commonBasePath, h):
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
    accuracy = []
    time = []
    for algo in algosVec:
        resultPath = commonBasePath + "/" + algo + str(h)
        if os.path.exists(resultPath):
            time_19, test_accuracy = extract_info(resultPath)
            accuracy.append(float(test_accuracy))
            time.append(float(time_19))
        else:
            accuracy.append(100)
            time.append(0)
    return time, accuracy


def main():
    soSpace = os.path.abspath(os.path.join(os.getcwd(), "../../..")) + "/"
    torch.ops.load_library(soSpace + "libIntelliStream.so")
    commonBasePath = (
        os.path.abspath(os.path.join(os.getcwd(), "../..")) + "/results/downstream_trainning"
    )
    os.system("mkdir -p ../../results")
    os.system("mkdir -p ../../figures")
    os.system("mkdir -p " + commonBasePath)
    runAll(commonBasePath)
    time, accuracy = parseResult(commonBasePath, 500)
    time2000, accuracy2000 = parseResult(commonBasePath, 2000)
    return time, accuracy, time2000, accuracy2000


if __name__ == "__main__":
    main()
