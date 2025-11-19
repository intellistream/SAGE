import torch

from ..functional.approx_linear import approx_linear_forward


class approx_linear_func(torch.autograd.Function):
    @staticmethod
    def forward(
        ctx,
        inputs,
        weights,
        bias,
        sample_ratio,
        minimal_k,
        sample_ratio_bwd,
        minimal_k_bwd,
        sample_ratio_wu,
        minimal_k_wu,
        algo,
    ):
        ctx.save_for_backward(inputs, weights, bias)
        # store non-tensor objects in ctx
        ctx.sample_ratio_bwd = sample_ratio_bwd
        ctx.minimal_k_bwd = minimal_k_bwd
        ctx.sample_ratio_wu = sample_ratio_wu
        ctx.minimal_k_wu = minimal_k_wu
        ctx.tag = algo
        # return approx_linear_forward(inputs, weights, bias,sample_ratio,minimal_k,None,None,None,None, tag=algo)
        return torch.nn.functional.linear(inputs, weights, bias)

    @staticmethod
    def backward(ctx, grad_output):
        inputs, weights, bias = ctx.saved_tensors
        if bias is not None:
            grad_bias = torch.sum(grad_output, 0)
        else:
            grad_bias = None

        if ctx.minimal_k_bwd is None:
            grad_input = torch.matmul(grad_output, weights)
        else:
            grad_input = approx_linear_forward(
                grad_output,
                weights.t(),
                None,
                ctx.sample_ratio_bwd,
                ctx.minimal_k_bwd,
                None,
                None,
                None,
                None,
                tag=ctx.tag,
            )

        if ctx.minimal_k_wu is None:
            grad_weight = torch.matmul(grad_output.t(), inputs)
        else:
            grad_weight = approx_linear_forward(
                grad_output.t(),
                inputs.t(),
                None,
                ctx.sample_ratio_wu,
                ctx.minimal_k_wu,
                None,
                None,
                None,
                None,
                tag=ctx.tag,
            )

        return grad_input, grad_weight, grad_bias, None, None, None, None, None, None, None
