# -*- coding: utf-8 -*-
"""
This file contains the algorithms for generating an embroidery pattern from an input image.

@author: Thorsten
"""

import io
import PIL.Image
import numpy as np
import sklearn.cluster as cl
import torch
import torchvision.transforms as T
from torchvision.models.detection import (
    MaskRCNN_ResNet50_FPN_Weights, maskrcnn_resnet50_fpn,
    MaskRCNN_ResNet50_FPN_V2_Weights, maskrcnn_resnet50_fpn_v2)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

def remove_background(image, score_threshold=0.75, num_objects=1, model_version="Version 1"):
    """
    Identifies the n largest objects and removes background.
    Returns: (PIL.Image, bool) -> The processed image and a success flag.
    """
    print(f"Attempting background removal ({model_version}, Threshold: {score_threshold}, Objects: {num_objects})...")
    try:
        # ... [Keep model selection and prediction code as is] ...
        if model_version == "Version 2":
            weights = MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT
            model = maskrcnn_resnet50_fpn_v2(weights=weights)
        else:
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
            high_conf_indices = torch.where(scores > score_threshold)[0]

            if len(high_conf_indices) > 0:
                mask_list = []
                for idx in high_conf_indices:
                    current_mask = (masks[idx, 0] > 0.5).cpu().numpy()
                    current_area = np.sum(current_mask)
                    mask_list.append((current_area, current_mask))
                
                mask_list.sort(key=lambda x: x[0], reverse=True)
                selected_masks = [m[1] for m in mask_list[:num_objects]]

                if selected_masks:
                    combined_mask = np.logical_or.reduce(selected_masks)
                    img_np = np.array(image)
                    background = np.full(img_np.shape, 255, dtype=np.uint8)
                    masked_img_np = np.where(combined_mask[:, :, None], img_np, background)
                    # RETURN SUCCESS
                    return PIL.Image.fromarray(masked_img_np), True
        
        # Return failure: No objects found
        return image, False
    except Exception as e:
        print(f"Background removal failed: {e}")
        # Return failure: Error occurred
        return image, False

def generate_embroidery_pattern(image, kmeans_n_clusters=20, crosses_x=150):
    rawdata = np.asarray(image.convert("RGB"))
    h, w, c = rawdata.shape
    
    data = rawdata.reshape(h * w, c)
    kmeans = cl.MiniBatchKMeans(n_clusters=kmeans_n_clusters, batch_size=10000, n_init='auto', random_state=42).fit(data)
    mapping = kmeans.predict(data).reshape(h, w)
    cluster_centers = kmeans.cluster_centers_

    step = max(5, w // crosses_x)
    grid_w, grid_h = w // step, h // step
    matrix = np.zeros((grid_h, grid_w), dtype='uint8')

    for i in range(grid_h):
        for j in range(grid_w):
            quadrat = mapping[i * step:(i + 1) * step, j * step:(j + 1) * step]
            count = np.bincount(quadrat.flatten(), minlength=len(cluster_centers))
            matrix[i, j] = np.argmax(count) if np.sum(count) > 0 else 0

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
            slice_obj[0, :], slice_obj[-1, :], slice_obj[:, 0], slice_obj[:, -1] = [0,0,0], [0,0,0], [0,0,0], [0,0,0]

    return {"pil_image": PIL.Image.fromarray(out), "cluster_centers": cluster_centers, "matrix": matrix}

def save_as_pdf(file_path, pattern_data, title_text, pagesize=A4):
    """
    Saves PDF with dynamic pagesize (A4 or A3).
    """
    pil_image = pattern_data['pil_image']
    cluster_centers = pattern_data['cluster_centers']
    matrix = pattern_data['matrix']

    c = canvas.Canvas(file_path, pagesize=pagesize)
    width, height = pagesize

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 2 * cm, title_text)

    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    img_w, img_h = pil_image.size
    scaling = min((width - 4 * cm) / img_w, (height / 2) / img_h)
    draw_w, draw_h = img_w * scaling, img_h * scaling
    c.drawImage(ImageReader(img_byte_arr), (width - draw_w) / 2, height - 3 * cm - draw_h, width=draw_w, height=draw_h)

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
    pattern_data['pil_image'].save(file_path, format='JPEG')

def update_pattern_at_coord(pattern_data, row, col, color_rgb):
    """
    Updates a single cell in the pattern data and redraws the cross in the PIL image.
    """
    matrix = pattern_data['matrix']
    pil_image = pattern_data['pil_image']
    cluster_centers = pattern_data['cluster_centers']
    
    # Update matrix color (find index or add new)
    # For simplicity, we can also just update the PIL image directly.
    # To keep the PDF export working, we find the closest cluster index or handle 'white'
    
    # Redraw the cross on the PIL image
    img_np = np.array(pil_image)
    h, w, _ = img_np.shape
    grid_h, grid_w = matrix.shape
    step = h // grid_h
    breadth = max(1, step // 8)
    
    y0, x0 = row * step, col * step
    y1, x1 = (row + 1) * step, (col + 1) * step
    
    # Clear cell to white
    img_np[y0:y1, x0:x1] = [255, 255, 255]
    
    # Draw cross if color is not white
    if not all(c == 255 for c in color_rgb):
        for r in range(step):
            for b_off in range(-breadth // 2, breadth - breadth // 2):
                if 0 <= r + b_off < step: 
                    img_np[y0 + r, x0 + r + b_off] = color_rgb
                if 0 <= (step - 1 - r) + b_off < step: 
                    img_np[y0 + r, x0 + (step - 1 - r) + b_off] = color_rgb
                    
    # Draw border
    img_np[y0:y1, x0] = [0,0,0]
    img_np[y0:y1, x1-1] = [0,0,0]
    img_np[y0, x0:x1] = [0,0,0]
    img_np[y1-1, x0:x1] = [0,0,0]

    pattern_data['pil_image'] = PIL.Image.fromarray(img_np)
    
    # Find cluster index for the matrix (to ensure PDF export stays consistent)
    # If it's manual deletion (white), we check if white is in cluster_centers
    # or just assign a neutral value.
    return pattern_data
