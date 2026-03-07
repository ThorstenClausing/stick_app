# -*- coding: utf-8 -*-
"""
This file contains the algorithms for generating an embroidery pattern from an input image.

@author: thors
"""

import PIL
import numpy as np
import sklearn.cluster as cl

# Import for background removal functionality
import torch
import torchvision.transforms as T
# Using the new weights API for torchvision models (post v0.13)
from torchvision.models.detection import MaskRCNN_ResNet50_FPN_Weights #maskrcnn_resnet50_fpn_weights
from torchvision.models.detection import maskrcnn_resnet50_fpn

def muster_generieren(eingabe_datei, ausgabe_datei, remove_background, kmeans_n_clusters, crosses_x):
    """
    Generates an embroidery pattern from an image.

    This function takes an image file as input and converts it into an
    embroidery pattern by using K-Means clustering to identify dominant colors
    and then representing them in a grid pattern of stitches.

    Args:
       eingabe_datei (str): The path to the input image file.
       ausgabe_datei (str): The path to save the generated embroidery pattern.
       remove_background (bool): If True, attempts to identify the main object
                                 and remove its background using a pre-trained
                                 Mask R-CNN model from torchvision.
       kmeans_n_clusters (int): The number of dominant colors to identify using K-Means.
       crosses_x (int): The desired number of embroidery "crosses" horizontally.
                        The vertical number will be scaled proportionally based on image aspect ratio.

     Returns: None
    """

    image = PIL.Image.open(eingabe_datei).convert("RGB") # Ensure image is in RGB format

    if remove_background:
        print("Attempting to remove background using Mask R-CNN...")
        try:
            # 1. Load pre-trained Mask R-CNN model
            # DEFAULT weights means COCO_V1 for this model, trained on COCO dataset.
            weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
            model = maskrcnn_resnet50_fpn(weights=weights)
            model.eval() # Set the model to evaluation mode for inference

            # 2. Define transforms to convert PIL Image to PyTorch Tensor
            preprocess = T.Compose([T.ToTensor()])

            # 3. Preprocess the image
            img_tensor = preprocess(image)

            # 4. Perform inference
            with torch.no_grad(): # Disable gradient calculations for inference
                # Model expects a list of images, even if only one
                prediction = model([img_tensor])

            # 5. Process predictions to find the main object and its mask
            if prediction and len(prediction[0]['scores']) > 0:
                scores = prediction[0]['scores']
                masks = prediction[0]['masks']
                boxes = prediction[0]['boxes']

                # Filter by a confidence threshold
                score_threshold = 0.75 # A common threshold for object detection. Adjust as needed.
                high_conf_indices = torch.where(scores > score_threshold)[0]

                if len(high_conf_indices) > 0:
                    # Find the mask with the largest area among high-confidence detections
                    max_area = 0
                    main_object_mask = None

                    for idx in high_conf_indices:
                        # Convert mask probabilities to a binary mask (e.g., > 0.5)
                        current_mask = (masks[idx, 0] > 0.5).cpu().numpy() # Squeeze channel dim, convert to numpy
                        current_area = np.sum(current_mask) # Calculate area of the binary mask

                        if current_area > max_area:
                            max_area = current_area
                            main_object_mask = current_mask

                    if main_object_mask is not None:
                        # Apply the mask to the original image
                        img_np = np.array(image)

                        # Create a white background
                        background = np.full(img_np.shape, 255, dtype=np.uint8)

                        # Use the mask to select foreground pixels from img_np,
                        # and background pixels from the white 'background' array.
                        # main_object_mask is (H, W), img_np is (H, W, 3).
                        # We broadcast the mask to (H, W, 3) for element-wise selection.
                        masked_img_np = np.where(main_object_mask[:, :, None], img_np, background)

                        image = PIL.Image.fromarray(masked_img_np)
                        print(f"Background removed successfully. Main object with area {max_area} identified.")
                    else:
                        print("No dominant object found with sufficient confidence after filtering for area. Proceeding with original image.")
                else:
                    print(f"No objects found above confidence threshold ({score_threshold}). Proceeding with original image.")
            else:
                print("No objects detected by the model. Proceeding with original image.")

        except Exception as e:
            print(f"An error occurred during background removal: {e}. Proceeding with original image.")
            # Ensure the model is not accidentally left on GPU if there was an error
            if 'model' in locals() and hasattr(model, 'to'):
                model.to('cpu') # Move model to CPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache() # Clear GPU memory cache

    rawdata = np.asarray(image)
    a, b, c = rawdata.shape # height, width, channels

    # Handle very small input images gracefully
    if a < 5 or b < 5:
        print(f"Error: Input image dimensions ({a}x{b}) are too small for pattern generation.")
        new_image = PIL.Image.new("RGB", (1, 1), (255, 255, 255))
        new_image.save(ausgabe_datei, format='jpeg')
        return
        
    data = rawdata.reshape(a * b, c) # Reshape for K-Means

    # Use MiniBatchKMeans
    kmeans = cl.MiniBatchKMeans(n_clusters=kmeans_n_clusters, batch_size=10000, n_init='auto', random_state=42).fit(data)
    mapping = kmeans.predict(data) # Assign each pixel to a cluster
    cc = kmeans.cluster_centers_ # Get the representative color for each cluster

    # Reshape the mapping back to the original image dimensions
    mapping = mapping.reshape(a, b)

    # Calculate step size based on desired horizontal crosses (crosses_x)
    # Ensure step is at least 5 to prevent division by zero or overly large grids
    step = max(5, b // crosses_x)
    
    # Calculate the actual number of grid cells that fit horizontally and vertically
    # This ensures that slicing `mapping` will always be within bounds.
    actual_grid_width = b // step
    actual_grid_height = a // step

    if actual_grid_height < 1 or actual_grid_width < 1:
        print(f"Warning: Image dimensions ({a}x{b}) are too small, or 'step' ({step}) is too large, for generating a meaningful grid ({actual_grid_height}x{actual_grid_width}). Output will be a minimal white image.")
        new_image = PIL.Image.new("RGB", (1, 1), (255, 255, 255))
        new_image.save(ausgabe_datei, format='jpeg')
        return

    # Use the actual calculated grid dimensions for the matrix
    matrix = np.zeros((actual_grid_height, actual_grid_width), dtype='uint8')

    # Create a matrix representing the dominant color in each grid cell
    for i in range(actual_grid_height):
        for j in range(actual_grid_width):
            quadrat = mapping[i * step:(i + 1) * step, j * step:(j + 1) * step]
            
            # Efficiently count occurrences of each cluster index using bincount
            # np.bincount requires non-negative integers. mapping values are 0 to n_clusters-1.
            count = np.bincount(quadrat.flatten(), minlength=len(cc))
            
            if np.sum(count) == 0:
                matrix[i, j] = 0 # Default to the first color if cell is empty or has no identifiable clusters
            else:
                matrix[i, j] = np.argmax(count) # Assign dominant color for the cell

    # Create the output embroidery pattern image
    output_image_height = actual_grid_height * step
    output_image_width = actual_grid_width * step
    
    out = np.empty((output_image_height, output_image_width, 3), dtype="uint8")
    
    # Calculate breadth for stitch thickness, ensure it's at least 1 for visible lines
    breadth = max(1, step // 8)

    for i in range(actual_grid_height):
        for j in range(actual_grid_width):
            # Get the dominant color for the current cell, ensure it's uint8
            col = cc[matrix[i, j]].astype(np.uint8)
            
            # Reference the specific slice in the output image for the current cell
            quadrat_slice = out[i * step:(i + 1) * step, j * step:(j + 1) * step]
            
            quadrat_slice[:, :] = [255, 255, 255]  # Set cell background to white

            # Draw cross-stitch 'X' pattern with specified thickness
            for k_row in range(step):
                for b_offset in range(-breadth // 2, breadth - breadth // 2): # Iterate for thickness
                    # Diagonal 1: top-left to bottom-right (y=x)
                    k_col_diag1 = k_row + b_offset
                    if 0 <= k_col_diag1 < step: # Ensure within cell bounds
                        quadrat_slice[k_row, k_col_diag1] = col

                    # Diagonal 2: top-right to bottom-left (y = step-1-x)
                    k_col_diag2 = (step - 1 - k_row) + b_offset
                    if 0 <= k_col_diag2 < step: # Ensure within cell bounds
                        quadrat_slice[k_row, k_col_diag2] = col
                        
            # Set border to black *within the current cell*
            quadrat_slice[0, :] = [0, 0, 0] # Top border
            quadrat_slice[-1, :] = [0, 0, 0] # Bottom border
            quadrat_slice[:, 0] = [0, 0, 0] # Left border
            quadrat_slice[:, -1] = [0, 0, 0] # Right border

    # Set the final outer border for the entire image (this will overwrite the last row/col of the last cells)
    if output_image_height > 0:
        out[output_image_height - 1, :] = [0, 0, 0] # Last row
    if output_image_width > 0:
        out[:, output_image_width - 1] = [0, 0, 0] # Last column

    new_image = PIL.Image.fromarray(out)
    new_image.save(ausgabe_datei, format='jpeg')
    print(f"Embroidery pattern generated and saved to {ausgabe_datei}")
