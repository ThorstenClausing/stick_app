# -*- coding: utf-8 -*-
"""
This file contains the algorithms for generating an embroidery pattern from an input image.

Created on Sun Apr 28 15:44:24 2024

@author: Thorsten
"""

import PIL
import numpy as np
import sklearn.cluster as cl

def muster_generieren(eingabe_datei, ausgabe_datei):
    """
    Generates an embroidery pattern from an image.

    This function takes an image file as input and converts it into an 
    embroidery pattern by using K-Means clustering to identify dominant colors
    and then representing them in a grid pattern of stitches.

    Args:
        eingabe_datei (str): The path to the input image file.
        ausgabe_datei (str): The path to save the generated embroidery pattern.

    Returns:
        None
    """
    image = PIL.Image.open(eingabe_datei)
    rawdata = np.asarray(image)
    a, b, c = rawdata.shape
    data = rawdata.reshape(a * b, c)

    # Use KMeans clustering to identify dominant colors
    kmeans = cl.MiniBatchKMeans(n_clusters=20, batch_size=10000, n_init='auto').fit(data)
    mapping = kmeans.predict(data)
    cc = kmeans.cluster_centers_

    # Reshape the mapping to the original image dimensions
    mapping = mapping.reshape(a, b)

    # Define the grid dimensions
    crosses_x = 150
    step = max(1, b // crosses_x)  # Ensure step is at least 1
    matrix = np.zeros((a // step, crosses_x), dtype='uint8')

    # Create a matrix representing the dominant color in each grid cell
    for i in range(a // step):
        for j in range(crosses_x):
            quadrat = mapping[i * step:(i + 1) * step, j * step:(j + 1) * step]
            count = np.zeros(len(cc))
            for k in range(len(cc)):
                count[k] = np.sum(quadrat == k)
            matrix[i, j] = np.argmax(count)

    # Create the output image
    out = np.empty(((a // step) * step, crosses_x * step, 3), dtype="uint8")
    breadth = step // 8
    for i in range(a // step):
        for j in range(crosses_x):
            col = cc[matrix[i, j]]
            quadrat = out[i * step:(i + 1) * step, j * step:(j + 1) * step]
            quadrat[:, :] = [255, 255, 255]  # Set background to white
            for k in range(2, step - 2):
                # Apply stitch pattern
                quadrat[k, max(k - breadth, 2):min(step - 2, k + breadth)] = col
                quadrat[k, max(2 - step, -breadth - k):min(-2, breadth - k)] = col
            # Set border to black
            quadrat[0] = [0, 0, 0]
            quadrat[:, 0] = [0, 0, 0]
    # Set final row and column to black
    out[-1] = [0, 0, 0]
    out[:, -1] = [0, 0, 0]

    newImage = PIL.Image.fromarray(out)
    newImage.save(ausgabe_datei, format='jpeg')
