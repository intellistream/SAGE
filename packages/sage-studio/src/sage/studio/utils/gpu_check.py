import ctypes.util
import shutil
import subprocess


def is_gpu_available() -> bool:
    """Check if NVIDIA GPU is available."""
    # 1. Check for nvidia-smi
    if shutil.which("nvidia-smi") is None:
        return False

    # 2. Check for libcuda.so
    if ctypes.util.find_library("cuda") is None:
        return False

    try:
        # 3. Run nvidia-smi to verify it works
        subprocess.check_call(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, OSError):
        return False
