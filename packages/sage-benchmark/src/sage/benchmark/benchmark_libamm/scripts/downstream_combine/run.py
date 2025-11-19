"""
Train MLPs for MNIST (adapted from https://github.com/lancopku/meProp/tree/master/src/pytorch)
"""

import os
import sys
from argparse import ArgumentParser

import torch
from data import get_mnist
from util import TestGroup


def get_args():
    parser = ArgumentParser()
    parser.add_argument("--n_epoch", type=int, default=20, help="number of training epochs")
    parser.add_argument("--d_hidden", type=int, default=500, help="dimension of hidden layers")
    parser.add_argument(
        "--n_layer", type=int, default=3, help="number of layers, including the output layer"
    )
    parser.add_argument("--d_minibatch", type=int, default=50, help="size of minibatches")
    parser.add_argument("--dropout", type=float, default=0.1, help="dropout rate")
    parser.add_argument("--random_seed", type=int, default=42, help="random seed")
    parser.add_argument("--dev", type=str, default="cpu", help='specify "cuda" or "cpu"')
    parser.set_defaults()
    args = parser.parse_args()
    args.device = torch.device("cpu")

    return args


def main(a, h=500):
    args = get_args()
    args.d_hidden = h
    trn, dev, tst = get_mnist()

    # change the sys.stdout to a file object to write the results to the file
    group = TestGroup(
        args,
        trn,
        args.d_minibatch,
        args.d_hidden,
        args.n_layer,
        args.dropout,
        dev,
        tst,
        cudatensor=False,
        file=sys.stdout,
        a=a,
    )

    # results may be different at each run
    # with torch.autograd.profiler.profile(use_cuda=True) as prof:
    group.run()
    # print(prof.key_averages())


if __name__ == "__main__":
    soSpace = os.path.abspath(os.path.join(os.getcwd(), "../../../../..")) + "/"
    torch.ops.load_library(soSpace + "libIntelliStream.so")
    main()
