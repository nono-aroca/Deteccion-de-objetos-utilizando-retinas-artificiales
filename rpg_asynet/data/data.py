#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np

def loadEventsFile( file_name):
        f = open(file_name, 'rb')
        raw_data = np.fromfile(f, dtype=np.uint8)
        f.close()
        raw_data = np.uint32(raw_data)
        print(len(raw_data))
        
file = 'N-Caltech101_object_detection/Caltech101/ant/image_0001.bin'
loadEventsFile(file)