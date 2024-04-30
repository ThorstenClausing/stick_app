# -*- coding: utf-8 -*-
"""
Diese Datei enthält die Algorithmen zur Erzeugung einer Stickvorlage aus einem Eingangsbild

Created on Sun Apr 28 15:44:24 2024

@author: Thorsten
"""

import PIL

import numpy as np

import sklearn.cluster as cl

def muster_generieren(eingabe_datei,ausgabe_datei):
    image = PIL.Image.open(eingabe_datei)
    rawdata = np.asarray(image)
    a,b,c = rawdata.shape
    data = rawdata.reshape(a*b,c)          
    kmeans = cl.MiniBatchKMeans(n_clusters=20,batch_size=10000,n_init='auto').fit(data)
    mapping = kmeans.predict(data)
    cc = kmeans.cluster_centers_
    mapping = mapping.reshape(a,b)
    crosses_x = 150
    step = b//crosses_x
    if step == 0:
        step = 1
    matrix = np.zeros((a//step,crosses_x),dtype='uint8')
    for i in range(a//step):
        for j in range (crosses_x):
            quadrat = mapping[i*step:(i+1)*step,j*step:(j+1)*step]
            count = np.zeros(len(cc))
            for k in range(len(cc)):
                count[k] = np.sum(quadrat == k)
            matrix[i,j] = np.argmax(count)

    out = np.empty(((a//step)*step,crosses_x*step,3),dtype="uint8")
    breadth = step//8
    for i in range(a//step):
        for j in range (crosses_x):
            col = cc[matrix[i,j]]
            quadrat = out[i*step:(i+1)*step,j*step:(j+1)*step]
            quadrat[:,:] = [255,255,255]
            for k in range(2,step-2):
                quadrat[k,max(k-breadth,2):min(step-2,k+breadth)] = col
                quadrat[k,max(2-step,-breadth-k):min(-2,breadth-k)] = col
            quadrat[0] = [0,0,0]
            quadrat[:,0] = [0,0,0]
    out[-1] = [0,0,0]
    out[:,-1] = [0,0,0]

    newImage = PIL.Image.fromarray(out)
    newImage.save(ausgabe_datei, format='jpeg')