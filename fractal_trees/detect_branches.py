#!/usr/bin/env python3
"""
Detect branch points in fractal tree images using morphological operations.
A branch point is where 3 or more lines meet.
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.spatial.distance import cdist

def load_and_preprocess(image_path):
    """Load image and convert to binary."""
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Threshold to binary (invert so branches are white)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    
    return img, binary

def skeletonize(binary_img):
    """Skeletonize the binary image."""
    # Ensure binary is 0 and 1
    skeleton = binary_img.copy() // 255
    
    # Zhang-Suen skeletonization
    from skimage.morphology import skeletonize as sk_skeletonize
    skeleton = sk_skeletonize(skeleton.astype(bool)).astype(np.uint8) * 255
    
    return skeleton

def detect_branch_points(skeleton):
    """
    Detect branch points using morphological operations.
    A branch point has 3 or more neighbors in the skeleton.
    """
    # Ensure skeleton is binary (0 and 1)
    skel = (skeleton > 0).astype(np.uint8)
    
    # Create kernel for counting neighbors (3x3 neighborhood)
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]], dtype=np.uint8)
    
    # Count neighbors for each pixel
    neighbor_count = ndimage.convolve(skel, kernel, mode='constant')
    
    # Branch points have 3 or more neighbors AND are part of the skeleton
    branch_points = ((neighbor_count >= 3) & (skel == 1)).astype(np.uint8)
    
    return branch_points

def select_fruit_positions(branch_points, n_fruits=35, min_distance=100, edge_margin=150):
    """
    Select well-spaced branch points for fruit placement using soft selection.
    
    Parameters:
    -----------
    branch_points : numpy array
        Binary image with branch points
    n_fruits : int
        Number of fruits to place
    min_distance : float
        Minimum distance between selected points (soft constraint)
    edge_margin : float
        Margin from edges to avoid (soft constraint)
    
    Returns:
    --------
    selected_points : list of tuples
        List of (x, y) coordinates for fruit placement
    """
    # Get all branch point coordinates
    branch_coords = np.argwhere(branch_points > 0)  # Returns (y, x) pairs
    
    if len(branch_coords) == 0:
        return []
    
    # Get image dimensions
    h, w = branch_points.shape
    
    # Calculate soft weights for each point based on distance from edges
    # Use sigmoid-like function for smooth falloff near edges
    y_coords = branch_coords[:, 0]
    x_coords = branch_coords[:, 1]
    
    # Distance to nearest edge
    dist_to_edge = np.minimum.reduce([
        y_coords,
        h - y_coords,
        x_coords,
        w - x_coords
    ])
    
    # Soft weight (sigmoid): close to 1 far from edges, close to 0 near edges
    edge_weights = 1 / (1 + np.exp(-0.05 * (dist_to_edge - edge_margin)))
    
    # Normalize to probabilities
    edge_weights = edge_weights / edge_weights.sum()
    
    selected_indices = []
    remaining_weights = edge_weights.copy()
    
    for _ in range(min(n_fruits, len(branch_coords))):
        if remaining_weights.sum() < 1e-10:
            break
            
        # Sample based on current weights
        remaining_weights = remaining_weights / remaining_weights.sum()
        idx = np.random.choice(len(branch_coords), p=remaining_weights)
        selected_indices.append(idx)
        
        # Get selected point
        selected_point = branch_coords[idx]
        
        # Calculate distances from selected point to all others
        distances = np.sqrt(
            (branch_coords[:, 0] - selected_point[0])**2 + 
            (branch_coords[:, 1] - selected_point[1])**2
        )
        
        # Soft suppression: reduce weights of nearby points
        # Use smooth falloff instead of hard threshold
        suppression = 1 / (1 + np.exp(-0.02 * (distances - min_distance)))
        remaining_weights *= suppression
        
        # Zero out the selected point
        remaining_weights[idx] = 0
    
    # Convert to (x, y) format
    selected_points = [(int(branch_coords[i, 1]), int(branch_coords[i, 0])) 
                      for i in selected_indices]
    
    return selected_points

def load_fruit_images(fruit_names=['Lemon.png', 'Orange.png', 'Apple.png', 'Banana.png'], size=80):
    """Load and resize fruit images with transparency."""
    fruits = []
    for name in fruit_names:
        try:
            img = cv2.imread(name, cv2.IMREAD_UNCHANGED)
            if img is not None:
                # Resize to desired size
                img = cv2.resize(img, (size, size))
                fruits.append(img)
            else:
                print(f"Warning: Could not load {name}")
        except Exception as e:
            print(f"Error loading {name}: {e}")
    
    return fruits

def overlay_image_alpha(background, overlay, x, y):
    """
    Overlay an image with alpha channel onto background at position (x, y).
    """
    h, w = overlay.shape[:2]
    
    # Calculate the region of interest
    y1, y2 = max(0, y - h//2), min(background.shape[0], y + h//2 + h%2)
    x1, x2 = max(0, x - w//2), min(background.shape[1], x + w//2 + w%2)
    
    # Calculate overlay region
    oy1 = h//2 - (y - y1)
    oy2 = h//2 + (y2 - y)
    ox1 = w//2 - (x - x1)
    ox2 = w//2 + (x2 - x)
    
    if x2 <= x1 or y2 <= y1:
        return background
    
    # Extract alpha channel if present
    if overlay.shape[2] == 4:
        alpha = overlay[oy1:oy2, ox1:ox2, 3] / 255.0
        alpha = alpha[:, :, np.newaxis]
        
        # Blend
        overlay_rgb = cv2.cvtColor(overlay[oy1:oy2, ox1:ox2, :3], cv2.COLOR_BGR2RGB)
        background_roi = background[y1:y2, x1:x2]
        
        blended = overlay_rgb * alpha + background_roi * (1 - alpha)
        background[y1:y2, x1:x2] = blended.astype(np.uint8)
    else:
        overlay_rgb = cv2.cvtColor(overlay[oy1:oy2, ox1:ox2], cv2.COLOR_BGR2RGB)
        background[y1:y2, x1:x2] = overlay_rgb
    
    return background

def visualize_results(original, skeleton, branch_points, output_path):
    """Visualize the original image, skeleton, and detected branch points."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Original image
    if len(original.shape) == 3:
        axes[0].imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
    else:
        axes[0].imshow(original, cmap='gray')
    axes[0].set_title('Original Image')
    axes[0].axis('off')
    
    # Skeleton
    axes[1].imshow(skeleton, cmap='gray')
    axes[1].set_title('Skeletonized')
    axes[1].axis('off')
    
    # Branch points overlaid on original
    # Create overlay
    overlay = cv2.cvtColor(original, cv2.COLOR_BGR2RGB) if len(original.shape) == 3 else cv2.cvtColor(original, cv2.COLOR_GRAY2RGB)
    
    # Mark branch points in red
    branch_coords = np.where(branch_points > 0)
    for y, x in zip(branch_coords[0], branch_coords[1]):
        cv2.circle(overlay, (x, y), 15, (255, 0, 0), -1)
    
    axes[2].imshow(overlay)
    axes[2].set_title(f'Branch Points Detected: {len(branch_coords[0])}')
    axes[2].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved visualization to: {output_path}")
    
    return len(branch_coords[0])

def create_fruit_tree(original, branch_points, fruit_positions, fruit_images, output_path):
    """Create visualization with fruits on selected branch points."""
    # Create base image
    result = cv2.cvtColor(original, cv2.COLOR_BGR2RGB) if len(original.shape) == 3 else cv2.cvtColor(original, cv2.COLOR_GRAY2RGB)
    
    # Place fruits
    for i, (x, y) in enumerate(fruit_positions):
        if len(fruit_images) > 0:
            fruit = fruit_images[i % len(fruit_images)]
            result = overlay_image_alpha(result, fruit, x, y)
    
    # Save result
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.imshow(result)
    ax.set_title(f'Fractal Tree with {len(fruit_positions)} Fruits')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved fruit tree to: {output_path}")
    
    return result

def main():
    # Input and output paths
    input_image = 'trees_another.png'
    output_image = 'trees_another_branch_analysis.png'
    output_fruit_tree = 'trees_another_with_fruits.png'
    
    print(f"Loading image: {input_image}")
    original, binary = load_and_preprocess(input_image)
    
    print("Skeletonizing...")
    skeleton = skeletonize(binary)
    
    print("Detecting branch points...")
    branch_points = detect_branch_points(skeleton)
    
    print("Creating visualization...")
    num_branches = visualize_results(original, skeleton, branch_points, output_image)
    
    print(f"\n{'='*50}")
    print(f"Analysis complete!")
    print(f"Total branch points detected: {num_branches}")
    print(f"{'='*50}\n")
    
    # Now add fruits!
    print("Selecting fruit positions...")
    n_fruits = 35
    fruit_positions = select_fruit_positions(
        branch_points, 
        n_fruits=n_fruits,
        min_distance=150,  # Pixels between fruits
        edge_margin=200    # Distance from edges
    )
    
    print(f"Selected {len(fruit_positions)} positions for fruits")
    
    # Load fruit images
    print("Loading fruit images...")
    fruit_images = load_fruit_images(
        fruit_names=['Lemon.png', 'Orange.png', 'Apple.png', 'Banana.png'],
        size=200  # Size of fruit images (2x each dimension = 4x area)
    )
    
    if len(fruit_images) == 0:
        print("Warning: No fruit images loaded!")
    else:
        print(f"Loaded {len(fruit_images)} fruit images")
        
        # Randomly shuffle fruit images for variety
        np.random.seed(42)  # For reproducibility
        random_fruits = [fruit_images[np.random.randint(len(fruit_images))] 
                        for _ in range(len(fruit_positions))]
        
        print("Creating fruit tree visualization...")
        create_fruit_tree(original, branch_points, fruit_positions, 
                         random_fruits, output_fruit_tree)
    
    print(f"\n{'='*50}")
    print(f"Fruit tree complete!")
    print(f"Total fruits placed: {len(fruit_positions)}")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()

