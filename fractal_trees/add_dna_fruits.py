#!/usr/bin/env python3
"""
Add fruits to tree images based on DNA sequence from ZFT_growing.txt
A -> Lemon (green)
T -> Apple (red)
C -> Banana (yellow)
G -> Orange (orange)
"""

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.morphology import skeletonize
from pathlib import Path

# DNA to Fruit mapping
DNA_TO_FRUIT = {
    'A': 'Lemon.png',
    'T': 'Apple.png',
    'C': 'Banana.png',
    'G': 'Orange.png'
}

def load_and_preprocess(image_path):
    """Load image and convert to binary."""
    img = cv2.imread(str(image_path))
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

def skeletonize_image(binary_img):
    """Skeletonize the binary image."""
    skeleton = binary_img.copy() // 255
    skeleton = skeletonize(skeleton.astype(bool)).astype(np.uint8) * 255
    return skeleton

def detect_branch_points(skeleton):
    """Detect branch points using morphological operations."""
    skel = (skeleton > 0).astype(np.uint8)
    
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]], dtype=np.uint8)
    
    neighbor_count = ndimage.convolve(skel, kernel, mode='constant')
    branch_points = ((neighbor_count >= 3) & (skel == 1)).astype(np.uint8)
    
    return branch_points

def select_fruit_positions(branch_points, n_fruits, min_distance=150, edge_margin=200):
    """Select well-spaced branch points for fruit placement."""
    branch_coords = np.argwhere(branch_points > 0)
    
    if len(branch_coords) == 0 or n_fruits == 0:
        return []
    
    h, w = branch_points.shape
    
    # Calculate soft weights based on distance from edges
    y_coords = branch_coords[:, 0]
    x_coords = branch_coords[:, 1]
    
    dist_to_edge = np.minimum.reduce([
        y_coords,
        h - y_coords,
        x_coords,
        w - x_coords
    ])
    
    edge_weights = 1 / (1 + np.exp(-0.05 * (dist_to_edge - edge_margin)))
    edge_weights = edge_weights / edge_weights.sum()
    
    selected_indices = []
    remaining_weights = edge_weights.copy()
    
    for _ in range(min(n_fruits, len(branch_coords))):
        if remaining_weights.sum() < 1e-10:
            break
            
        remaining_weights = remaining_weights / remaining_weights.sum()
        idx = np.random.choice(len(branch_coords), p=remaining_weights)
        selected_indices.append(idx)
        
        selected_point = branch_coords[idx]
        
        distances = np.sqrt(
            (branch_coords[:, 0] - selected_point[0])**2 + 
            (branch_coords[:, 1] - selected_point[1])**2
        )
        
        suppression = 1 / (1 + np.exp(-0.02 * (distances - min_distance)))
        remaining_weights *= suppression
        remaining_weights[idx] = 0
    
    selected_points = [(int(branch_coords[i, 1]), int(branch_coords[i, 0])) 
                      for i in selected_indices]
    
    return selected_points

def load_fruit_image(fruit_name, size=200):
    """Load and resize a single fruit image."""
    img = cv2.imread(fruit_name, cv2.IMREAD_UNCHANGED)
    if img is not None:
        img = cv2.resize(img, (size, size))
    return img

def overlay_image_alpha(background, overlay, x, y):
    """Overlay an image with alpha channel onto background."""
    h, w = overlay.shape[:2]
    
    y1, y2 = max(0, y - h//2), min(background.shape[0], y + h//2 + h%2)
    x1, x2 = max(0, x - w//2), min(background.shape[1], x + w//2 + w%2)
    
    oy1 = h//2 - (y - y1)
    oy2 = h//2 + (y2 - y)
    ox1 = w//2 - (x - x1)
    ox2 = w//2 + (x2 - x)
    
    if x2 <= x1 or y2 <= y1:
        return background
    
    if overlay.shape[2] == 4:
        alpha = overlay[oy1:oy2, ox1:ox2, 3] / 255.0
        alpha = alpha[:, :, np.newaxis]
        
        overlay_rgb = cv2.cvtColor(overlay[oy1:oy2, ox1:ox2, :3], cv2.COLOR_BGR2RGB)
        background_roi = background[y1:y2, x1:x2]
        
        blended = overlay_rgb * alpha + background_roi * (1 - alpha)
        background[y1:y2, x1:x2] = blended.astype(np.uint8)
    else:
        overlay_rgb = cv2.cvtColor(overlay[oy1:oy2, ox1:ox2], cv2.COLOR_BGR2RGB)
        background[y1:y2, x1:x2] = overlay_rgb
    
    return background

def process_tree_with_dna(tree_num, dna_sequence, tree_dir, fruit_dir, output_dir):
    """Process a single tree image with DNA-based fruits."""
    # Load tree image
    tree_path = tree_dir / f"{tree_num}.png"
    original, binary = load_and_preprocess(tree_path)
    
    # Skip if no fruits to add
    if len(dna_sequence) == 0:
        print(f"  Tree {tree_num}: No fruits (empty sequence)")
        return
    
    # Detect branch points
    skeleton = skeletonize_image(binary)
    branch_points = detect_branch_points(skeleton)
    
    # Select positions for fruits
    n_fruits = len(dna_sequence)
    fruit_positions = select_fruit_positions(
        branch_points,
        n_fruits=n_fruits,
        min_distance=150,
        edge_margin=200
    )
    
    # Convert to RGB for fruit overlay
    result = cv2.cvtColor(original, cv2.COLOR_BGR2RGB) if len(original.shape) == 3 else cv2.cvtColor(original, cv2.COLOR_GRAY2RGB)
    
    # Load fruits and place them according to DNA sequence
    for i, nucleotide in enumerate(dna_sequence):
        if i >= len(fruit_positions):
            break
            
        fruit_name = DNA_TO_FRUIT.get(nucleotide)
        if fruit_name is None:
            continue
            
        fruit_path = fruit_dir / fruit_name
        fruit_img = load_fruit_image(str(fruit_path), size=200)
        
        if fruit_img is not None:
            x, y = fruit_positions[i]
            result = overlay_image_alpha(result, fruit_img, x, y)
    
    # Save result
    output_path = output_dir / f"{tree_num}.png"
    result_pil = Image.fromarray(result)
    result_pil.save(output_path)
    
    print(f"  Tree {tree_num}: Added {len(dna_sequence)} fruits ({dna_sequence})")

def main():
    # Set up paths
    base_dir = Path('.')
    tree_dir = base_dir / 'tree_variations'
    fruit_dir = base_dir
    output_dir = base_dir / 'with_fruits'
    dna_file = base_dir / 'ZFT_growing.txt'
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Read DNA sequences
    print("Reading DNA sequences from ZFT_growing.txt...")
    with open(dna_file, 'r') as f:
        dna_sequences = [line.strip() for line in f.readlines()]
    
    print(f"Found {len(dna_sequences)} DNA sequences")
    print(f"Processing 50 trees with DNA-based fruits...")
    print()
    
    # Process each tree
    for tree_num in range(1, 51):
        if tree_num - 1 < len(dna_sequences):
            dna_sequence = dna_sequences[tree_num - 1]
            process_tree_with_dna(tree_num, dna_sequence, tree_dir, fruit_dir, output_dir)
        else:
            print(f"  Tree {tree_num}: Skipped (no DNA sequence)")
    
    print()
    print("=" * 60)
    print("Complete! All trees with DNA fruits saved to with_fruits/")
    print("=" * 60)

if __name__ == '__main__':
    main()

