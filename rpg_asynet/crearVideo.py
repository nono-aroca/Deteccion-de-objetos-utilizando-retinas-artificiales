#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import os
from os.path import isfile, join


def convertToVideo(pathIn, pathOut, fps, time):
    frame_array = []
    files = [f for f in os.listdir(pathIn) if isfile(join(pathIn, f))]
    files.sort()#REORDENA FRAMES
    print(files)
    for i in range(len(files)):
        filename = pathIn+files[i]
        print(filename)
        img=cv2.imread(filename)
        height, width, layers = img.shape
        size = (width,height)

#        for k in range (time):
#            frame_array.append(img)
        frame_array.append(img)

    out = cv2.VideoWriter(pathOut, cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
    for i in range(len(frame_array)):
        out.write(frame_array[i])
    out.release()
    print("TASK COMPLETED")

#EJECUTAMOS  FUNCIÓN.

def crearVideo(filepath):
    directory = filepath
    fps = 10
    time = int(len(os.listdir(filepath)) / 10)
    pathIn = directory + '/'
    pathOut=pathIn + 'video.avi' 
    convertToVideo(pathIn, pathOut, fps, time)