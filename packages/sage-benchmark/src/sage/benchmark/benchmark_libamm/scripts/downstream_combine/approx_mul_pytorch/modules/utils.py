def topk_indices(data, k):
    # as of pytorch v1.1.0, it turns out that torch.sort[:k] is faster than torch.topk
    # return torch.topk(data,k)[1]
    return data.argsort(descending=True)[:k]
