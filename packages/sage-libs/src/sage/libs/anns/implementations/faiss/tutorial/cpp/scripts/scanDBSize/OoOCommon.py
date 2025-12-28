import csv
import numpy as np
import matplotlib.pyplot as plt
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
import matplotlib.ticker as mtick

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


def editConfig(src, dest, key, value):
    df = pd.read_csv(src, header=None)
    rowIdx = 0
    idxt = 0
    for cell in df[0]:
        # print(cell)
        if (cell == key):
            rowIdx = idxt
            break
        idxt = idxt + 1
    df[1][rowIdx] = str(value)
    df.to_csv(dest, index=False, header=False)


def readConfig(src, key):
    df = pd.read_csv(src, header=None)
    rowIdx = 0
    idxt = 0
    for cell in df[0]:
        # print(cell)
        if (cell == key):
            rowIdx = idxt
            break
        idxt = idxt + 1
    return df[1][rowIdx]


def draw2yLine(NAME, Com, R1, R2, l1, l2, m1, m2, fname):
    fig, ax1 = plt.subplots(figsize=(10, 6.4))
    lines = [None] * 2
    # ax1.set_ylim(0, 1)
    print(Com)
    print(R1)
    lines[0], = ax1.plot(Com, R1, color=LINE_COLORS[0], \
                         linewidth=LINE_WIDTH, marker=MARKERS[0], \
                         markersize=MARKER_SIZE
                         #
                         )

    # #plt.show()
    ax1.set_ylabel(m1, fontproperties=LABEL_FP)
    ax1.set_xlabel(NAME, fontproperties=LABEL_FP)
    # ax1.set_xticklabels(ax1.get_xticklabels())  # 设置共用的x轴
    plt.xticks(rotation=0, size=TICK_FONT_SIZE)
    plt.yticks(rotation=0, size=TICK_FONT_SIZE)
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    ax2 = ax1.twinx()

    # ax2.set_ylabel('latency/us')
    # ax2.set_ylim(0, 0.5)
    lines[1], = ax2.plot(Com, R2, color=LINE_COLORS[1], \
                         linewidth=LINE_WIDTH, marker=MARKERS[1], \
                         markersize=MARKER_SIZE)

    ax2.set_ylabel(m2, fontproperties=LABEL_FP)
    # ax2.vlines(192000, min(R2)-1, max(R2)+1, colors = "GREEN", linestyles = "dashed",label='total L1 size')
    # plt.grid(axis='y', color='gray')

    # style = dict(size=10, color='black')
    # ax2.hlines(tset, 0, x2_list[len(x2_list)-1]+width, colors = "r", linestyles = "dashed",label="tset")
    # ax2.text(4, tset, "$T_{set}$="+str(tset)+"us", ha='right', **style)

    # plt.xlabel('batch', fontproperties=LABEL_FP)

    # plt.xscale('log')
    # figure.xaxis.set_major_locator(LinearLocator(5))
    ax1.yaxis.set_major_locator(LinearLocator(5))
    ax2.yaxis.set_major_locator(LinearLocator(5))
    ax1.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))
    ax2.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))
    ax1.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))
    ax2.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1f'))
    plt.legend(lines,
               [l1, l2],
               prop=LEGEND_FP,
               loc='upper center',
               ncol=1,
               bbox_to_anchor=(0.55, 1.3
                               ), shadow=False,
               columnspacing=0.1,
               frameon=True, borderaxespad=-1.5, handlelength=1.2,
               handletextpad=0.1,
               labelspacing=0.1)
    plt.yticks(rotation=0, size=TICK_FONT_SIZE)
    plt.tight_layout()

    plt.savefig(fname + ".pdf")
