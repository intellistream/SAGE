"""
Helper class to facilitate experiments (adapted from https://github.com/lancopku/meProp/tree/master/src/pytorch)
"""

import sys
import time
from statistics import mean

import torch
import torch.cuda
import torch.nn.functional as F
import torch.optim as optim
import torch.utils.data
from model import MLP
from torch.autograd import Variable


class TestGroup:
    """
    Test groups differ in minibatch size, hidden features, layer number and dropout rate.
    """

    def __init__(
        self,
        args,
        trnset,
        mb,
        hidden,
        layer,
        dropout,
        devset=None,
        tstset=None,
        cudatensor=False,
        file=sys.stdout,
        a="mm",
    ):
        self.args = args
        self.mb = mb
        self.hidden = hidden
        self.layer = layer
        self.dropout = dropout
        self.file = file
        self.trnset = trnset
        self.algo = a

        if cudatensor:  # dataset is on GPU
            self.trainloader = torch.utils.data.DataLoader(trnset, batch_size=mb, num_workers=0)
            if tstset:
                self.testloader = torch.utils.data.DataLoader(tstset, batch_size=mb, num_workers=0)
            else:
                self.testloader = None
        else:  # dataset is on CPU, using prefetch and pinned memory to shorten the data transfer time
            self.trainloader = torch.utils.data.DataLoader(
                trnset,
                batch_size=mb,
                shuffle=True,
                num_workers=1,
                # num_workers=0,
                pin_memory=True,
            )
            if devset:
                self.devloader = torch.utils.data.DataLoader(
                    devset,
                    batch_size=mb,
                    shuffle=False,
                    num_workers=1,
                    # num_workers=0,
                    pin_memory=True,
                )
            else:
                self.devloader = None
            if tstset:
                self.testloader = torch.utils.data.DataLoader(
                    tstset,
                    batch_size=mb,
                    shuffle=False,
                    num_workers=1,
                    # num_workers=0,
                    pin_memory=True,
                )
            else:
                self.testloader = None
        self.basettime = None
        self.basebtime = None

    def reset(self):
        """
        Reinit the trainloader at the start of each run,
        so that the traning examples is in the same random order
        """
        torch.manual_seed(self.args.random_seed)
        self.trainloader = torch.utils.data.DataLoader(
            self.trnset,
            batch_size=self.mb,
            shuffle=True,
            num_workers=1,
            # num_workers=0,
            pin_memory=True,
        )

    def _train(self, model, opt):
        """
        Train the given model using the given optimizer
        Record the time and loss
        """
        # compare_grad_vs_approx = True
        compare_grad_vs_approx = False
        model.train()
        ftime = 0
        btime = 0
        utime = 0
        tloss = 0

        if compare_grad_vs_approx:
            num_approx_layers = 0
            for layer in model.children():
                for sublayer in layer.children():
                    # print(sublayer.__class__.__name__)
                    if sublayer.__class__.__name__ == "approx_Linear":
                        for n, p in sublayer.named_parameters():
                            # print(p.size())
                            if "weight" in n:
                                num_approx_layers += 1

            avg_mean = torch.zeros(num_approx_layers, len(self.trainloader))
            avg_mse = torch.zeros(num_approx_layers, len(self.trainloader))
            avg_std = torch.zeros(num_approx_layers, len(self.trainloader))

        for bid, (data, target) in enumerate(self.trainloader):
            data, target = data.to(self.args.device), target.view(-1).to(self.args.device)
            # with torch.autograd.profiler.profile(use_cuda=True) as prof:
            # start = torch.cuda.Event(True)
            # end = torch.cuda.Event(True)

            if compare_grad_vs_approx:
                # get gradients with non-approximate calculations:
                acc_grads = []
                for layer in model.children():
                    for sublayer in layer.children():
                        if sublayer.__class__.__name__ == "approx_Linear":
                            sublayer.eval()

                opt.zero_grad()
                output = model(data)
                loss = F.nll_loss(output, target)
                loss.backward()
                for layer in model.children():
                    for sublayer in layer.children():
                        if sublayer.__class__.__name__ == "approx_Linear":
                            for n, p in sublayer.named_parameters():
                                if "weight" in n:
                                    acc_grads.append(p.grad.clone())

                approx_grads = []
                model.train()
                opt.zero_grad()
                output = model(data)
                loss = F.nll_loss(output, target)
                loss.backward()
                for layer in model.children():
                    for sublayer in layer.children():
                        if sublayer.__class__.__name__ == "approx_Linear":
                            for n, p in sublayer.named_parameters():
                                if "weight" in n:
                                    approx_grads.append(p.grad.clone())

                opt.step()
                tloss += loss.item()
                tloss /= len(self.trainloader)
                # print('approx_grads:')
                # print (approx_grads)
                # print ('acc_grads')
                # print (acc_grads)
                # print('mean {}'.format(torch.mean(avg_mean,dim=1)))
                # print('relative MSE {}'.format(torch.mean(avg_mse,dim=1)))
                # print('std {}'.format(torch.mean(avg_std,dim=1)))
                for i, (approx_grad, acc_grad) in enumerate(zip(approx_grads, acc_grads)):
                    # print('index {}'.format(i))
                    # print('mean {}'.format((approx_grad-acc_grad).flatten().mean()))
                    avg_mean[i, bid] = (approx_grad - acc_grad).flatten().mean()
                    # print('relative MSE {}'.format((approx_grad-acc_grad).norm()/acc_grad.norm()))
                    avg_mse[i, bid] = (approx_grad - acc_grad).norm() / acc_grad.norm()
                    # print('std {}'.format((approx_grad-acc_grad).flatten().std()))
                    avg_std[i, bid] = (approx_grad - acc_grad).flatten().std()

            else:
                # start.record()
                opt.zero_grad()
                # end.record()
                # end.synchronize()
                # utime += start.elapsed_time(end)

                # start.record()
                output = model(data)
                loss = F.nll_loss(output, target)
                # end.record()
                # end.synchronize()
                # ftime += start.elapsed_time(end)

                # start.record()
                loss.backward()
                # end.record()
                # end.synchronize()
                # btime += start.elapsed_time(end)

                # start.record()
                opt.step()
                # end.record()
                # end.synchronize()
                # utime += start.elapsed_time(end)

                tloss += loss.item()

                tloss /= len(self.trainloader)
                # print(prof.key_averages())

        if compare_grad_vs_approx:
            print(f"mean {torch.mean(avg_mean, dim=1)}")
            print(f"relative MSE {torch.mean(avg_mse, dim=1)}")
            print(f"std {torch.mean(avg_std, dim=1)}")

        return tloss, ftime, btime, utime

    def _evaluate(self, model, loader, name="test"):
        """
        Use the given model to classify the examples in the given data loader
        Record the loss and accuracy.
        """
        model.eval()
        test_loss = 0
        correct = 0
        for data, target in loader:
            data, target = (
                Variable(
                    # data, requires_grad=False).cuda(), Variable(target).cuda()
                    data,
                    requires_grad=False,
                ).to(self.args.device),
                Variable(target).to(self.args.device),
            )
            output = model(data)
            test_loss += F.nll_loss(output, target).item()
            pred = output.data.max(1)[1]  # get the index of the max log-probability
            correct += pred.eq(target.data).cpu().sum()

        test_loss = test_loss
        test_loss /= len(loader)  # loss function already averages over batch size
        print(
            f"{name} set: Average loss: {test_loss:.4f}, Accuracy: {correct}/{len(loader.dataset)} ({100.0 * float(correct) / len(loader.dataset):.2f}%)",
            file=self.file,
            flush=True,
        )
        return 100.0 * float(correct) / len(loader.dataset)

    def run(self, epoch=None):
        """
        Run a training loop.
        """
        if epoch is None:
            epoch = self.args.n_epoch
        print(
            f"mbsize: {self.mb}, hidden size: {self.hidden}, layer: {self.layer}, dropout: {self.dropout}",
            file=self.file,
        )
        # Init the model, the optimizer and some structures for logging
        self.reset()

        model = MLP(self.hidden, self.layer, self.dropout, self.algo)
        # print(model)
        model.reset_parameters()
        # model.cuda()
        model.to(self.args.device)
        # model = torch.nn.DataParallel(model)
        opt = optim.Adam(model.parameters())

        acc = 0  # best dev. acc.
        accc = 0  # test acc. at the time of best dev. acc.
        e = -1  # best dev iteration/epoch

        losses = []
        ftime = []
        btime = []
        utime = []

        print("Initial evaluation on dev set:")
        self._evaluate(model, self.devloader, "dev")

        start = time.time()
        # training loop
        for t in range(epoch):
            print(f"{t}：", end="", file=self.file, flush=True)
            # train

            # start = torch.cuda.Event(True)
            # end = torch.cuda.Event(True)
            # start.record()
            loss, ft, bt, ut = self._train(model, opt)
            # end.record()
            # end.synchronize()
            # ttime = start.elapsed_time(end)
            print(f"(wall time: {time.time() - start:.1f} sec) ", end="")
            # times.append(ttime)
            losses.append(loss)
            ftime.append(ft)
            btime.append(bt)
            utime.append(ut)
            # predict
            self._evaluate(model, self.devloader, "dev")
            # if curacc > acc:
            #    e = t
            #    acc = curacc
            #    accc = self._evaluate(model, self.testloader, '    test')
        [sum(t) for t in zip(ftime, btime, utime)]
        print("test acc: {:.2f}".format(self._evaluate(model, self.testloader, "    test")))
        print(f"best on val set - ${acc:.2f}|{accc:.2f} at {e}", file=self.file, flush=True)
        print("", file=self.file)

    def _stat(self, name, t, agg=mean):
        return "{:<5}:\t{:8.3f}; {}".format(name, agg(t), ", ".join([f"{x:8.2f}" for x in t]))
