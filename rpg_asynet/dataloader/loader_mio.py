#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import torch
import numpy as np

from torch.utils.data.dataloader import default_collate


class Loader:
    def __init__(self, dataset, batch_size, num_workers, pin_memory, device, shuffle=False): #parametros no por defecto???  batch_size???
        self.device = device
#        split_indices = list(range(len(dataset)))
        print('aqui')
#        if shuffle:
#            sampler = torch.utils.data.sampler.SubsetRandomSampler(split_indices)
#            self.loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, sampler=sampler,
#                                                      num_workers=num_workers, pin_memory=pin_memory,
#                                                      collate_fn=collate_events)
#        else:
#            self.loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size,
#                                                      num_workers=num_workers, pin_memory=pin_memory,
#                                                      collate_fn=collate_events)
#        sampler = torch.utils.data.sampler.SequentialSampler(split_indices)
#        self.loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, sampler=sampler,
#                                                      num_workers=num_workers, pin_memory=pin_memory,
#                                                      collate_fn=collate_events)
        self.loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size,
                                                  num_workers=num_workers, pin_memory=pin_memory,
                                                  collate_fn=collate_events)
    def __iter__(self):
        for data in self.loader:
            data = [d.to(self.device) for d in data]
            yield data

    def __len__(self):
        return len(self.loader)


def collate_events(data):
    events = []
    histograms = []
    for i, d in enumerate(data):
        histograms.append(d[1])
        ev = np.concatenate([d[0], i*np.ones((len(d[0]), 1), dtype=np.float32)], 1)
        events.append(ev)
    events = torch.from_numpy(np.concatenate(events, 0))

    histograms = default_collate(histograms)

    return events, histograms