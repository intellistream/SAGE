import torch
import time

print("PyTorch 版本:", torch.__version__)

# 检查 CUDA 是否可用
if torch.cuda.is_available():
    print("CUDA is available. GPU数量:", torch.cuda.device_count())
    print("当前GPU:", torch.cuda.get_device_name(0))

    # 做个简单的矩阵运算测性能
    x = torch.randn(10000, 10000, device="cuda")
    y = torch.randn(10000, 10000, device="cuda")
    torch.cuda.synchronize()
    start = time.time()
    z = torch.mm(x, y)
    torch.cuda.synchronize()
    print("10000x10000矩阵乘法耗时: {:.3f} 秒".format(time.time() - start))
else:
    print("CUDA 不可用，当前只用CPU")
