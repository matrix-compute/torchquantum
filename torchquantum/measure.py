import functools
import torch
import torch.nn as nn
import torchquantum as tq
import numpy as np

from torchquantum.macro import F_DTYPE
from typing import Union, List


def expval(q_device: tq.QuantumDevice,
           wires: Union[int, List[int]],
           observables: Union[tq.Observable, List[tq.Observable]]):

    all_dims = np.arange(q_device.states.dim())
    if isinstance(wires, int):
        wires = [wires]
        observables = [observables]

    # rotation to the desired basis
    for wire, observable in zip(wires, observables):
        for rotation in observable.diagonalizing_gates():
            rotation(q_device, wires=wire)

    states = q_device.states
    # compute magnitude
    state_mag = torch.abs(states) ** 2

    expectations = []
    for wire, observable in zip(wires, observables):
        # compute marginal magnitude
        reduction_dims = np.delete(all_dims, [0, wire + 1])
        probs = state_mag.sum(list(reduction_dims))
        res = probs.mv(observable.eigvals.real.to(probs.device))
        expectations.append(res)

    return torch.stack(expectations, dim=-1)


class MeasureAll(tq.QuantumModule):
    def __init__(self, obs, q_c_reg_mapping=None):
        super().__init__()
        self.obs = obs
        self.q_c_reg_mapping = q_c_reg_mapping

    def forward(self, q_device: tq.QuantumDevice):
        self.q_device = q_device
        x = expval(q_device, list(range(q_device.n_wires)), [self.obs()] *
                   q_device.n_wires)

        if self.q_c_reg_mapping is not None:
            c2q_mapping = self.q_c_reg_mapping['c2q']
            """
            the measurement is not normal order, need permutation 
            """
            perm = []
            for k in range(x.shape[-1]):
                if k in c2q_mapping.keys():
                    perm.append(c2q_mapping[k])
            x = x[:, perm]

        return x

    def set_q_c_reg_mapping(self, mapping):
        self.q_c_reg_mapping = mapping
