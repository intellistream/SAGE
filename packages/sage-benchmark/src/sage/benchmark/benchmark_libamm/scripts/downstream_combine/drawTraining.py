import io
import sys

import numpy as np
from draw import main as runAll
from run import main as runError


def main():
    time, accuracy, time2, accuracy2 = runAll()
    time, accuracy = (
        [50 * (element - time[-1] * 0.78) for element in time],
        [(100 - element) / 100 for element in accuracy],
    )
    time2, accuracy2 = (
        [50 * (element - time2[-1] * 0.78) for element in time2],
        [(100 - element) / 100 for element in accuracy2],
    )
    # print(time,accuracy)
    time[0] = time[0] / time[-2] * time[-1]
    time2[0] = time2[0] / time2[-2] * time2[-1]
    ammE = []
    ammE2 = []
    for algo in [
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
    ]:
        if algo == "vq" or algo == "pq":
            ammE.append(0)
            ammE2.append(0)
        else:
            new_stdout = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = new_stdout
            try:
                # Call your method
                runError(a="e" + algo, h=500)
            except Exception:
                # Ignore the error and continue
                pass
            finally:
                # Reset stdout
                sys.stdout = old_stdout
                # Store the captured output
                out = new_stdout.getvalue()
                for line in out.splitlines():
                    if algo in line:
                        ammE.append(float(line.split(" ")[-1]))
            new_stdout = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = new_stdout
            try:
                # Call your method
                runError(a="e" + algo, h=2000)
            except Exception:
                # Ignore the error and continue
                pass
            finally:
                # Reset stdout
                sys.stdout = old_stdout
                # Store the captured output
                out = new_stdout.getvalue()
                for line in out.splitlines():
                    if algo in line:
                        ammE2.append(float(line.split(" ")[-1]))

    return (
        np.array(time),
        np.array(accuracy),
        np.array(ammE),
        np.array(time2),
        np.array(accuracy2),
        np.array(ammE2),
    )


main()
