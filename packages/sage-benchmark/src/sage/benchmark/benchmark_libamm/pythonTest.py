import torch


def main():
    # load the library, assume it is located together with this file

    # gen the input tensor
    a = torch.rand(100, 100)
    b = torch.rand(100, 100)
    # The pytorch +
    print("/****test add****/")
    print("pytorch-mm:", torch.matmul(a, b))
    # our c++ extension of +
    torch.ops.load_library("../libLibAMM.so")
    torch.ops.LibAMM.setTag("mm")
    print("LibAMM-MM+:", torch.ops.LibAMM.ammDefault(a, b))
    torch.ops.LibAMM.setTag("crs")
    print("LibAMM-CRS+:", torch.ops.LibAMM.ammDefault(a, b))


if __name__ == "__main__":
    main()
