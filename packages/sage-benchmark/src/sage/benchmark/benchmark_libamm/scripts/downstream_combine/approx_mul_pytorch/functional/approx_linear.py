import torch

from ..modules.utils import *  # noqa: F403

count = 0
error = 0


def approx_linear_forward(
    input,
    weight,
    bias,
    sample_ratio,
    minimal_k,
    sample_ratio_bwd,
    minimal_k_bwd,
    sample_ratio_wu,
    minimal_k_wu,
    tag,
):
    r"""
    Applies approximate linear transformation to the incoming data: :math:`y = xA^T + b`.
    the matrix multiply xA^T is approximated
    note: weight transposition is done in this function
    Shape:
        - Input: :math:`(N, *, in\_features)` where `*` means any number of
          additional dimensions
        - Weight: :math:`(out\_features, in\_features)`
        - Bias: :math:`(out\_features)`
        - Output: :math:`(N, *, out\_features)`
    """

    return approx_linear_forward_xA_b(
        input,
        weight.t(),
        bias,
        sample_ratio,
        minimal_k,
        sample_ratio_bwd,
        minimal_k_bwd,
        sample_ratio_wu,
        minimal_k_wu,
        tag,
    )


def approx_linear_forward_xA_b(
    input,
    weight,
    bias,
    sample_ratio,
    minimal_k,
    sample_ratio_bwd,
    minimal_k_bwd,
    sample_ratio_wu,
    minimal_k_wu,
    tag,
):
    r"""
    Applies approximate linear transformation to the incoming data: :math:`y = xA + b`.
    Note: A is assumed not transposed
    the matrix multiply xA is approximated
    Shape:
        - Input: :math:`(N, *, in\_features)` where `*` means any number of
          additional dimensions
        - Weight: :math:`(in\_features, out\_features)`
        - Bias: :math:`(out\_features)`
        - Output: :math:`(N, *, out\_features)`
    """
    if tag.startswith("e"):
        tag = tag[1:]
        return ammE(input, weight, bias, minimal_k, tag)
    return amm(input, weight, bias, minimal_k, tag)


def ammE(A, B, bias, minimal_k, algo):
    torch.ops.LibAMM.setTag(algo)
    global count
    count += 1
    C = torch.ops.LibAMM.ammSpecifySs(A, B, minimal_k)
    CE = torch.mm(A, B)
    global error
    error += torch.norm(CE - C, p="fro")
    if count == 10:
        string = algo + ": " + str(error.item() / 10)
        print(string)
        count = 0
        error = 0
        return 1
    if bias is not None:
        C += bias
    return C


def amm(A, B, bias, minimal_k, algo):
    torch.ops.LibAMM.setTag(algo)
    C = torch.ops.LibAMM.ammSpecifySs(A, B, minimal_k)
    if bias is not None:
        C += bias
    return C
