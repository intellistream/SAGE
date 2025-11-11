import itertools as it
import os

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pylab
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import LogLocator

# 获取系统中可用的字体路径
# font_paths = fm.findSystemFonts()
# OPT_FONT_NAME = 'Helvetica'
TICK_FONT_SIZE = 20
LABEL_FONT_SIZE = 20
LEGEND_FONT_SIZE = 20
LABEL_FP = FontProperties(style="normal", size=LABEL_FONT_SIZE)
LEGEND_FP = FontProperties(style="normal", size=LEGEND_FONT_SIZE)
TICK_FP = FontProperties(style="normal", size=TICK_FONT_SIZE)

MARKERS = [
    "o",
    "s",
    "v",
    "^",
    "h",
    "v",
    ">",
    "x",
    "d",
    "<",
    "|",
    "p",
    "+",
    "_",
    "%",
    "|",
    "|",
    "|",
    "|",
    "|",
]
# you may want to change the color map for different figures
COLOR_MAP = (
    "#F15854",
    "#5DA5DA",
    "#60BD68",
    "#B276B2",
    "#DECF3F",
    "#F17CB0",
    "#B2912F",
    "#FAA43A",
    "#AFAFAF",
    "#087878",
    "#783456",
    "#560012",
    "#431256",
    "#00AABB",
    "#AA00BB",
)
# you may want to change the patterns for different figures
PATTERNS = [
    "|",
    "\\",
    "/",
    "+",
    "-",
    ".",
    "*",
    "x",
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
MARKER_SIZE = 13.0
MARKER_FREQUENCY = 1000

# matplotlib.rcParams['ps.useafm'] = True
# matplotlib.rcParams['pdf.use14corefonts'] = True
# matplotlib.rcParams['xtick.labelsize'] = TICK_FONT_SIZE
# matplotlib.rcParams['ytick.labelsize'] = TICK_FONT_SIZE
# 创建字体列表
# Explicitly specify the font path
# 获取系统中可用的字体路径
font_paths = fm.findSystemFonts()

# 创建字体列表
font_list = []
for font_path in font_paths:
    try:
        font_name = fm.FontProperties(fname=font_path).get_name()
        if font_name not in font_list:
            font_list.append(font_name)
    except:
        pass

# 配置 matplotlib 使用系统中可用的字体
plt.rcParams["font.family"] = font_list[0]

FIGURE_FOLDER = "/data1/xtra/results/figure"


# there are some embedding problems if directly exporting the pdf figure using matplotlib.
# so we generate the eps format first and convert it to pdf.
def ConvertEpsToPdf(dir_filename):
    os.system("epstopdf --outfile " + dir_filename + ".pdf " + dir_filename + ".eps")
    os.system("rm -rf " + dir_filename + ".eps")


def DrawLegend(legend_labels, filename):
    fig = pylab.figure()
    ax1 = fig.add_subplot(111)
    FIGURE_LABEL = legend_labels
    LINE_WIDTH = 8.0
    MARKER_SIZE = 12.0
    LEGEND_FP = FontProperties(style="normal", size=26)

    figlegend = pylab.figure(figsize=(12, 0.5))
    idx = 0
    lines = [None] * (len(FIGURE_LABEL))
    data = [1]
    x_values = [1]

    idx = 0
    for group in range(len(FIGURE_LABEL)):
        (lines[idx],) = ax1.plot(
            x_values,
            data,
            color=LINE_COLORS[idx],
            linewidth=LINE_WIDTH,
            marker=MARKERS[idx],
            markersize=MARKER_SIZE,
            label=str(group),
        )
        idx = idx + 1

    # LEGEND
    figlegend.legend(
        lines,
        FIGURE_LABEL,
        prop=LEGEND_FP,
        loc=1,
        ncol=len(FIGURE_LABEL),
        mode="expand",
        shadow=False,
        frameon=False,
        borderaxespad=0.0,
        handlelength=2,
    )

    if not os.path.exists(FIGURE_FOLDER):
        os.makedirs(FIGURE_FOLDER)
    # no need to export eps in this case.
    figlegend.savefig(filename + ".pdf")


# draw a line chart
def DrawFigure(
    xvalues, yvalues, legend_labels, x_label, y_label, y_min, y_max, filename, allow_legend
):
    # you may change the figure size on your own.
    fig = plt.figure(figsize=(10, 3))
    figure = fig.add_subplot(111)

    FIGURE_LABEL = legend_labels

    x_values = xvalues
    y_values = yvalues

    lines = [None] * (len(FIGURE_LABEL))
    for i in range(len(y_values)):
        (lines[i],) = figure.plot(
            x_values[i],
            y_values[i],
            color=LINE_COLORS[i],
            linewidth=LINE_WIDTH,
            marker=MARKERS[i],
            markersize=MARKER_SIZE,
            label=FIGURE_LABEL[i],
        )

    # sometimes you may not want to draw legends.
    if allow_legend == True:
        plt.legend(
            lines,
            FIGURE_LABEL,
            prop=LEGEND_FP,
            loc="upper center",
            ncol=3,
            # mode='expand',
            bbox_to_anchor=(0.55, 1.6),
            shadow=False,
            columnspacing=0.1,
            frameon=True,
            borderaxespad=0.0,
            handlelength=1.5,
            handletextpad=0.1,
            labelspacing=0.1,
        )
    plt.xscale("log")
    plt.yscale("log")
    # plt.yscale('log')

    # you may control the limits on your own.

    # plt.ylim(y_min, y_max)

    plt.grid(axis="y", color="gray")
    figure.yaxis.set_major_locator(LogLocator(base=10))
    figure.xaxis.set_major_locator(LogLocator(base=10))

    figure.get_xaxis().set_tick_params(direction="in", pad=10)
    figure.get_yaxis().set_tick_params(direction="in", pad=10)

    plt.xlabel(x_label, fontproperties=LABEL_FP)
    plt.ylabel(y_label, fontproperties=LABEL_FP)

    size = fig.get_size_inches()
    dpi = fig.get_dpi()

    # plt.show()
    plt.savefig(filename + ".pdf", bbox_inches="tight")


# draw a line chart
def DrawFigureXYnormal(
    xvalues, yvalues, legend_labels, x_label, y_label, y_min, y_max, filename, allow_legend
):
    # you may change the figure size on your own.
    fig = plt.figure(figsize=(10, 3))
    figure = fig.add_subplot(111)

    FIGURE_LABEL = legend_labels

    x_values = xvalues
    y_values = yvalues

    lines = [None] * (len(FIGURE_LABEL))
    for i in range(len(y_values)):
        (lines[i],) = figure.plot(
            x_values[i],
            y_values[i],
            color=LINE_COLORS[i],
            linewidth=LINE_WIDTH,
            marker=MARKERS[i],
            markersize=MARKER_SIZE,
            label=FIGURE_LABEL[i],
            markeredgecolor="k",
        )

    # sometimes you may not want to draw legends.
    if allow_legend == True:
        plt.legend(
            lines,
            FIGURE_LABEL,
            prop=LEGEND_FP,
            loc="upper center",
            ncol=3,
            bbox_to_anchor=(0.55, 1.5),
            shadow=False,
            columnspacing=0.1,
            frameon=True,
            borderaxespad=0,
            handlelength=1.2,
            handletextpad=0.1,
            labelspacing=0.1,
        )
    # plt.xscale('log')
    # plt.yscale('log')
    # plt.yscale('log')

    # you may control the limits on your own.

    # plt.ylim(y_min, y_max)

    plt.grid(axis="y", color="gray")
    plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号
    # figure.yaxis.set_major_locator(LogLocator(base=10))
    # figure.xaxis.set_major_locator(LogLocator(base=10))
    plt.xticks(rotation=0, fontsize=TICK_FONT_SIZE)
    figure.get_xaxis().set_tick_params(direction="in", pad=10)
    figure.get_yaxis().set_tick_params(direction="in", pad=10)

    plt.xlabel(x_label, fontproperties=LABEL_FP)
    plt.ylabel(y_label, fontproperties=LABEL_FP)

    size = fig.get_size_inches()
    dpi = fig.get_dpi()

    # plt.show()
    plt.savefig(filename + ".pdf", bbox_inches="tight")


# draw a line chart
def DrawFigureYnormal(
    xvalues, yvalues, legend_labels, x_label, y_label, y_min, y_max, filename, allow_legend
):
    # you may change the figure size on your own.
    fig = plt.figure(figsize=(10, 3))
    figure = fig.add_subplot(111)

    FIGURE_LABEL = legend_labels

    x_values = xvalues
    y_values = yvalues

    lines = [None] * (len(FIGURE_LABEL))
    for i in range(len(y_values)):
        (lines[i],) = figure.plot(
            x_values[i],
            y_values[i],
            color=LINE_COLORS[i],
            linewidth=LINE_WIDTH,
            marker=MARKERS[i],
            markersize=MARKER_SIZE,
            label=FIGURE_LABEL[i],
            markeredgecolor="k",
        )

    # sometimes you may not want to draw legends.
    if allow_legend == True:
        plt.legend(
            lines,
            FIGURE_LABEL,
            prop=LEGEND_FP,
            loc="upper center",
            ncol=3,
            bbox_to_anchor=(0.55, 1.5),
            shadow=False,
            columnspacing=0.1,
            frameon=True,
            borderaxespad=0,
            handlelength=1.2,
            handletextpad=0.1,
            labelspacing=0.1,
        )
    plt.xscale("log")
    # plt.yscale('log')
    # plt.yscale('log')

    # you may control the limits on your own.

    # plt.ylim(y_min, y_max)

    plt.grid(axis="y", color="gray")
    plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号
    # figure.yaxis.set_major_locator(LogLocator(base=10))
    # figure.xaxis.set_major_locator(LogLocator(base=10))
    plt.xticks(rotation=0, fontsize=TICK_FONT_SIZE)
    figure.get_xaxis().set_tick_params(direction="in", pad=10)
    figure.get_yaxis().set_tick_params(direction="in", pad=10)

    plt.xlabel(x_label, fontproperties=LABEL_FP)
    plt.ylabel(y_label, fontproperties=LABEL_FP)

    size = fig.get_size_inches()
    dpi = fig.get_dpi()

    # plt.show()
    plt.savefig(filename + ".pdf", bbox_inches="tight")


# example for reading csv file
def ReadFile():
    y = []
    col1 = []
    col2 = []
    col3 = []
    col4 = []
    col5 = []
    col6 = []
    col7 = []
    col8 = []

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/PRJ_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col1.append(value)
    y.append(col1)

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/NPJ_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col2.append(value)
    y.append(col2)

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/MPASS_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col3.append(value)
    y.append(col3)

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/MWAY_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col4.append(value)
    y.append(col4)

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/SHJ_JM_NP_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col5.append(value)
    y.append(col5)

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/SHJ_JBCR_NP_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col6.append(value)
    y.append(col6)

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/PMJ_JM_NP_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col7.append(value)
    y.append(col7)

    for id in it.chain(range(28, 32)):
        file = f"/data1/xtra/results/timestamps/PMJ_JBCR_NP_{id}.txt"
        f = open(file)
        read = f.readlines()
        x = float(read.pop(len(read) - 1).strip("\n"))  # get last timestamp
        value = len(read) / x  # get throughput (#items/ms)
        col8.append(value)
    y.append(col8)
    return y


if __name__ == "__main__":
    # x_values = ['Unique', 'Zipf(0)', 'Zipf(0.2)', 'Zipf(0.4)', 'Zipf(0.8)', 'Zipf(1)']
    x_values = [1600, 3200, 6400, 12800, 25600]

    y_values = ReadFile()

    legend_labels = [
        "NPJ",
        "PRJ",
        "MWAY",
        "MPASS",
        "SHJ$^{JM}$",
        "SHJ$^{JB}$",
        "PMJ$^{JM}$",
        "PMJ$^{JB}$",
    ]

    DrawFigure(
        x_values,
        y_values,
        legend_labels,
        "Input arrival rate of R (e/ms)",
        "Tpt. (#matches/ms)",
        x_values[0],
        x_values[4],
        "throughput_figure1_1",
        False,
    )

#   DrawLegend(legend_labels, 'factor_legend')
