import torch

from ..Function.approx_linear import approx_linear_func

# import approx_linear_xA_b


class approx_Linear(torch.nn.modules.Linear):
    r"""Applies approximate Linear transformation to the incoming data:

    Args:
        in_features: size of each input sample
        out_features: size of each output sample
        bias: If set to ``False``, the layer will not learn an additive bias.
            Default: ``True``
        sample_ratio - Ratio of column-row pairs to sample
        minimal_k - Minimal number of column-row pairs to keep in the sampling

    Shape:
        - Input: :math:`(N, *, H_{in})` where :math:`*` means any number of
          additional dimensions and :math:`H_{in} = \text{in\_features}`
        - Output: :math:`(N, *, H_{out})` where all but the last dimension
          are the same shape as the input and :math:`H_{out} = \text{out\_features}`.

    Attributes:
        weight: the learnable weights of the module of shape
            :math:`(\text{out\_features}, \text{in\_features})`. The values are
            initialized from :math:`\mathcal{U}(-\sqrt{k}, \sqrt{k})`, where
            :math:`k = \frac{1}{\text{in\_features}}`
        bias:   the learnable bias of the module of shape :math:`(\text{out\_features})`.
                If :attr:`bias` is ``True``, the values are initialized from
                :math:`\mathcal{U}(-\sqrt{k}, \sqrt{k})` where
                :math:`k = \frac{1}{\text{in\_features}}`


    """

    def __init__(
        self,
        in_features,
        out_features,
        bias=True,
        sample_ratio=1.0,
        minimal_k=1,
        sample_ratio_bwd=None,
        minimal_k_bwd=None,
        sample_ratio_wu=None,
        minimal_k_wu=None,
        algo="mm",
    ):
        self.sample_ratio = sample_ratio
        self.minimal_k = minimal_k
        self.sample_ratio_bwd = sample_ratio_bwd
        self.minimal_k_bwd = minimal_k_bwd
        self.sample_ratio_wu = sample_ratio_wu
        self.minimal_k_wu = minimal_k_wu
        self.algo = algo
        super().__init__(in_features, out_features, bias)

    def forward(self, input):
        if self.training is True:
            # Use approximation in training only.
            return approx_linear_func.apply(
                input,
                self.weight,
                self.bias,
                self.sample_ratio,
                self.minimal_k,
                self.sample_ratio_bwd,
                self.minimal_k_bwd,
                self.sample_ratio_wu,
                self.minimal_k_wu,
                self.algo,
            )
            # return approx_linear_forward(input, self.weight, self.bias, self.sample_ratio, self.minimal_k,self.sample_ratio_bwd,self.minimal_k_bwd,self.sample_ratio_wu,self.minimal_k_wu)
        else:
            # For evaluation, perform the exact computation
            return torch.nn.functional.linear(input, self.weight, self.bias)
