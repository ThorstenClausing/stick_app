# -*- coding: utf-8 -*-
"""
This file contains the algorithms for generating an embroidery pattern from an input image.

@author: thors
"""

import io
import os
import PIL.Image
import numpy as np
import sklearn.cluster as cl
import torch
import torchvision.transforms as T
from torchvision.models.detection import MaskRCNN_ResNet50_FPN_Weights, maskrcnn_resnet50_fpn
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

def remove_background(image):
    """
    Identifies the main object in an image and removes the background using Mask R-CNN.

    Args:
        image (PIL.Image): The input image.

    Returns:
        PIL.Image: The image with the background replaced by white pixels.
    """
    print("Attempting to remove background using Mask R-CNN...")
    try:
        weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
        model = maskrcnn_resnet50_fpn(weights=weights)
        model.eval()

        preprocess = T.Compose([T.ToTensor()])
        img_tensor = preprocess(image)

        with torch.no_grad():
            prediction = model([img_tensor])

        if prediction and len(prediction[0]['scores']) > 0:
            scores = prediction[0]['scores']
            masks = prediction[0]['masks']
            score_threshold = 0.75
            high_conf_indices = torch.where(scores > score_threshold)[0]

            if len(high_conf_indices) > 0:
                max_area = 0
                main_object_mask = None
                for idx in high_conf_indices:
                    current_mask = (masks[idx, 0] > 0.5).cpu().numpy()
                    current_area = np.sum(current_mask)
                    if current_area > max_area:
                        max_area = current_area
                        main_object_mask = current_mask

                if main_object_mask is not None:
                    img_np = np.array(image)
                    background = np.full(img_np.shape, 255, dtype=np.uint8)
                    masked_img_np = np.where(main_object_mask[:, :, None], img_np, background)
                    return PIL.Image.fromarray(masked_img_np)
        
        print("No dominant object detected. Returning original.")
        return image
    except Exception as e:
        print(f"Background removal failed: {e}")
        return image

def generate_embroidery_pattern(image, kmeans_n_clusters=20, crosses_x=150):
    """
    Transforms an image into an embroidery pattern data structure.

    Args:
        image (PIL.Image): The source image.
        kmeans_n_clusters (int): Number of colors to use.
        crosses_x (int): Horizontal resolution in stitches.

    Returns:
        dict: A dictionary containing 'pil_image' (the visual pattern), 
              'cluster_centers' (RGB values), and 'matrix' (color indices).
    """
    rawdata = np.asarray(image.convert("RGB"))
    h, w, c = rawdata.shape
    
    # 1. Clustering
    data = rawdata.reshape(h * w, c)
    kmeans = cl.MiniBatchKMeans(n_clusters=kmeans_n_clusters, batch_size=10000, n_init='auto', random_state=42).fit(data)
    mapping = kmeans.predict(data).reshape(h, w)
    cluster_centers = kmeans.cluster_centers_

    # 2. Grid Logic
    step = max(5, w // crosses_x)
    grid_w, grid_h = w // step, h // step
    matrix = np.zeros((grid_h, grid_w), dtype='uint8')

    for i in range(grid_h):
        for j in range(grid_w):
            quadrat = mapping[i * step:(i + 1) * step, j * step:(j + 1) * step]
            count = np.bincount(quadrat.flatten(), minlength=len(cluster_centers))
            matrix[i, j] = np.argmax(count) if np.sum(count) > 0 else 0

    # 3. Draw Pattern
    out = np.empty((grid_h * step, grid_w * step, 3), dtype="uint8")
    breadth = max(1, step // 8)

    for i in range(grid_h):
        for j in range(grid_w):
            col = cluster_centers[matrix[i, j]].astype(np.uint8)
            slice_obj = out[i * step:(i + 1) * step, j * step:(j + 1) * step]
            slice_obj[:, :] = [255, 255, 255]
            
            for r in range(step):
                for b_off in range(-breadth // 2, breadth - breadth // 2):
                    if 0 <= r + b_off < step: slice_obj[r, r + b_off] = col
                    if 0 <= (step - 1 - r) + b_off < step: slice_obj[r, (step - 1 - r) + b_off] = col
            
            # Cell Borders
            slice_obj[0, :], slice_obj[-1, :], slice_obj[:, 0], slice_obj[:, -1] = [0,0,0], [0,0,0], [0,0,0], [0,0,0]

    return {
        "pil_image": PIL.Image.fromarray(out),
        "cluster_centers": cluster_centers,
        "matrix": matrix
    }

def save_as_pdf(file_path, pattern_data, title_text):
    """
    Saves the embroidery pattern and its color legend to a PDF file.

    Args:
        file_path (str): Path to the output PDF.
        pattern_data (dict): Data returned by generate_embroidery_pattern.
        title_text (str): Title to display at the top of the PDF.
    """
    pil_image = pattern_data['pil_image']
    cluster_centers = pattern_data['cluster_centers']
    matrix = pattern_data['matrix']

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 2 * cm, title_text)

    # Pattern Image
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    img_w, img_h = pil_image.size
    scaling = min((width - 4 * cm) / img_w, (height / 2) / img_h)
    draw_w, draw_h = img_w * scaling, img_h * scaling
    c.drawImage(ImageReader(img_byte_arr), (width - draw_w) / 2, height - 3 * cm - draw_h, width=draw_w, height=draw_h)

    # Legend
    y_pos = height - 4 * cm - draw_h
    c.setFont("Helvetica", 12)
    c.drawString(2 * cm, y_pos, "Verwendete Farben (Color Legend):")
    y_pos -= 1 * cm

    unique_indices = np.unique(matrix)
    for idx in unique_indices:
        rgb = cluster_centers[idx].astype(int)
        c.setFillColor(colors.Color(rgb[0]/255, rgb[1]/255, rgb[2]/255))
        c.rect(2 * cm, y_pos, 0.5 * cm, 0.5 * cm, fill=1, stroke=1)
        c.setFillColor(colors.black)
        hex_val = '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])
        c.drawString(3 * cm, y_pos + 0.1 * cm, f"ID {idx}: RGB {tuple(rgb)} | {hex_val}")
        y_pos -= 0.7 * cm
        if y_pos < 2 * cm:
            c.showPage()
            y_pos = height - 2 * cm
    c.save()

def save_as_jpeg(file_path, pattern_data):
    """
    Saves the embroidery pattern image as a JPEG file.

    Args:
        file_path (str): Path to the output JPEG.
        pattern_data (dict): Data returned by generate_embroidery_pattern.
    """
    pattern_data['pil_image'].save(file_path, format='JPEG')