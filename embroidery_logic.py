# -*- coding: utf-8 -*-
"""
Core algorithms for processing images into embroidery patterns.
Includes background removal, color quantization, and grid visualization.
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
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# Constants for Paper Sizes
PAPER_SIZES = {
    "A4 Portrait": A4,
    "A4 Landscape": landscape(A4),
    "A3 Portrait": A3,
    "A3 Landscape": landscape(A3)
}

def remove_background(image, score_threshold=0.75, num_objects=1, model_version="Version 1"):
    """
    Uses Mask R-CNN to identify foreground objects and remove the background.

    Args:
        image (PIL.Image): Input image.
        score_threshold (float): Confidence threshold for AI detection.
        num_objects (int): Number of largest detected objects to keep.
        model_version (str): "Version 1" or "Version 2" of Mask R-CNN.

    Returns:
        tuple: (Processed PIL.Image, bool success_flag)
    """
    try:
        if model_version == "Version 2":
            weights = MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT
            model = maskrcnn_resnet50_fpn_v2(weights=weights)
        else:
            weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
            model = maskrcnn_resnet50_fpn(weights=weights)

        model.eval()
        img_tensor = T.ToTensor()(image)

        with torch.no_grad():
            prediction = model([img_tensor])

        if not prediction or len(prediction[0]['scores']) == 0:
            return image, False

        scores = prediction[0]['scores']
        masks = prediction[0]['masks']
        high_conf_indices = torch.where(scores > score_threshold)[0]

        if len(high_conf_indices) == 0:
            return image, False

        mask_list = []
        for idx in high_conf_indices:
            current_mask = (masks[idx, 0] > 0.5).cpu().numpy()
            mask_list.append((np.sum(current_mask), current_mask))

        # Sort by area descending and take top N
        mask_list.sort(key=lambda x: x[0], reverse=True)
        selected_masks = [m[1] for m in mask_list[:num_objects]]
        combined_mask = np.logical_or.reduce(selected_masks)

        img_np = np.array(image.convert("RGB"))
        masked_img = np.where(combined_mask[:, :, None], img_np, 255).astype(np.uint8)
        
        return PIL.Image.fromarray(masked_img), True

    except Exception as e:
        print(f"AI Background Removal Error: {e}")
        return image, False

def _draw_cell_cross(draw_area, step, color_rgb):
    """
    Helper to draw a single cross in a numpy array slice.
    """
    breadth = max(1, step // 8)
    draw_area[:, :] = [255, 255, 255] # Clear to white
    
    # Vectorized diagonal drawing
    for offset in range(-breadth // 2, breadth - breadth // 2 + 1):
        indices = np.arange(step)
        # Main diagonal
        valid_diag1 = (indices + offset >= 0) & (indices + offset < step)
        draw_area[indices[valid_diag1], (indices + offset)[valid_diag1]] = color_rgb
        # Anti-diagonal
        valid_diag2 = (step - 1 - indices + offset >= 0) & (step - 1 - indices + offset < step)
        draw_area[indices[valid_diag2], (step - 1 - indices + offset)[valid_diag2]] = color_rgb

    # Draw black borders
    draw_area[0, :] = draw_area[-1, :] = draw_area[:, 0] = draw_area[:, -1] = [0, 0, 0]

def generate_embroidery_pattern(image, kmeans_n_clusters=20, crosses_x=150):
    """
    Reduces image colors via K-Means and generates a cross-stitch grid.

    Args:
        image (PIL.Image): Input image.
        kmeans_n_clusters (int): Number of thread colors.
        crosses_x (int): Number of horizontal stitches.

    Returns:
        dict: Containing 'pil_image', 'cluster_centers', and 'matrix' (grid indices).
    """
    rawdata = np.asarray(image.convert("RGB"))
    h, w, _ = rawdata.shape
    
    # Color Quantization
    data = rawdata.reshape(-1, 3)
    kmeans = cl.MiniBatchKMeans(
        n_clusters=kmeans_n_clusters, 
        batch_size=10000, 
        n_init='auto', 
        random_state=42
    ).fit(data)
    mapping = kmeans.predict(data).reshape(h, w)
    centers = kmeans.cluster_centers_.astype(np.uint8)

    # Grid Calculation
    step = max(5, w // crosses_x)
    grid_w, grid_h = w // step, h // step
    matrix = np.zeros((grid_h, grid_w), dtype='uint8')

    # Assign most frequent color to each grid cell
    for i in range(grid_h):
        for j in range(grid_w):
            cell_data = mapping[i*step:(i+1)*step, j*step:(j+1)*step]
            if cell_data.size > 0:
                matrix[i, j] = np.bincount(cell_data.flatten()).argmax()

    # Create visualization
    out_np = np.ones((grid_h * step, grid_w * step, 3), dtype="uint8") * 255
    for i in range(grid_h):
        for j in range(grid_w):
            color = centers[matrix[i, j]]
            _draw_cell_cross(out_np[i*step:(i+1)*step, j*step:(j+1)*step], step, color)

    return {
        "pil_image": PIL.Image.fromarray(out_np),
        "cluster_centers": centers,
        "matrix": matrix
    }

def update_pattern_at_coord(pattern_data, row, col, color_idx):
    """
    Updates a specific cell in the grid and redraws that cell in the PIL image.

    Args:
        pattern_data (dict): The current pattern state.
        row, col (int): Grid coordinates.
        color_idx (int): Center index or 255 for eraser.

    Returns:
        dict: Updated pattern data.
    """
    matrix = pattern_data['matrix']
    img_np = np.array(pattern_data['pil_image'])
    centers = pattern_data['cluster_centers']
    
    h, w, _ = img_np.shape
    grid_h, grid_w = matrix.shape
    step = h // grid_h
    
    # Update state
    matrix[row, col] = color_idx
    
    # Redraw cell
    y0, x0 = row * step, col * step
    slice_area = img_np[y0:y0+step, x0:x0+step]
    
    if color_idx == 255:
        slice_area[:, :] = [255, 255, 255]
        slice_area[0, :] = slice_area[-1, :] = slice_area[:, 0] = slice_area[:, -1] = [0, 0, 0]
    else:
        _draw_cell_cross(slice_area, step, centers[color_idx])

    pattern_data['pil_image'] = PIL.Image.fromarray(img_np)
    pattern_data['matrix'] = matrix
    return pattern_data

def save_as_pdf(file_path, pattern_data, title, legend_text="Legend", pagesize=A4):
    """
    Exports the pattern and color legend to a PDF file.
    """
    c = canvas.Canvas(file_path, pagesize=pagesize)
    w_page, h_page = pagesize

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w_page / 2, h_page - 2 * cm, title)

    # Drawing the pattern image
    img_byte_arr = io.BytesIO()
    pattern_data['pil_image'].save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    img_w, img_h = pattern_data['pil_image'].size
    scaling = min((w_page - 4 * cm) / img_w, (h_page / 2) / img_h)
    draw_w, draw_h = img_w * scaling, img_h * scaling
    c.drawImage(ImageReader(img_byte_arr), (w_page - draw_w) / 2, h_page - 3 * cm - draw_h, width=draw_w, height=draw_h)

    # Legend
    y_pos = h_page - 4 * cm - draw_h
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y_pos, legend_text)
    y_pos -= 0.8 * cm

    c.setFont("Helvetica", 10)
    unique_indices = np.unique(pattern_data['matrix'])
    for idx in unique_indices:
        if idx == 255: continue
        rgb = pattern_data['cluster_centers'][idx]
        c.setFillColor(colors.Color(rgb[0]/255, rgb[1]/255, rgb[2]/255))
        c.rect(2 * cm, y_pos, 0.4 * cm, 0.4 * cm, fill=1, stroke=1)
        
        c.setFillColor(colors.black)
        hex_val = '#%02x%02x%02x' % tuple(rgb)
        c.drawString(2.6 * cm, y_pos + 0.1 * cm, f"ID {idx}: RGB {tuple(rgb)} | {hex_val}")
        
        y_pos -= 0.6 * cm
        if y_pos < 2 * cm:
            c.showPage()
            y_pos = h_page - 2 * cm

    c.save()

def save_as_jpeg(file_path, pattern_data):
    """Saves the pattern image as a JPEG."""
    pattern_data['pil_image'].convert("RGB").save(file_path, format='JPEG')