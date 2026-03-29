#!/usr/bin/env python3
"""
Pad all tree images to the same dimensions (the maximum dimensions found).
Centers the original content in the padded image.
"""

import os
from PIL import Image
from pathlib import Path

def find_max_dimensions(image_dir):
    """Find the maximum width and height among all PNG files."""
    max_width = 0
    max_height = 0
    
    png_files = sorted(Path(image_dir).glob("*.png"), key=lambda x: int(x.stem))
    
    for img_path in png_files:
        with Image.open(img_path) as img:
            width, height = img.size
            max_width = max(max_width, width)
            max_height = max(max_height, height)
            print(f"{img_path.name}: {width}x{height}")
    
    return max_width, max_height, len(png_files)

def pad_image(img_path, target_width, target_height):
    """Pad an image to target dimensions, centering the original content."""
    with Image.open(img_path) as img:
        width, height = img.size
        
        # If already at target size, skip
        if width == target_width and height == target_height:
            return False
        
        # Create new image with white background
        padded = Image.new('RGB', (target_width, target_height), (255, 255, 255))
        
        # Calculate position to center the original image
        x_offset = (target_width - width) // 2
        y_offset = (target_height - height) // 2
        
        # Paste the original image onto the padded canvas
        padded.paste(img, (x_offset, y_offset))
        
        # Save the padded image
        padded.save(img_path)
        return True

def main():
    image_dir = "tree_variations"
    
    print("=" * 60)
    print("Finding maximum dimensions...")
    print("=" * 60)
    
    max_width, max_height, num_images = find_max_dimensions(image_dir)
    
    print("\n" + "=" * 60)
    print(f"Maximum dimensions: {max_width} x {max_height}")
    print(f"Total images: {num_images}")
    print("=" * 60)
    
    print("\nPadding images to uniform size...")
    
    padded_count = 0
    png_files = sorted(Path(image_dir).glob("*.png"), key=lambda x: int(x.stem))
    
    for img_path in png_files:
        if pad_image(img_path, max_width, max_height):
            print(f"  Padded: {img_path.name}")
            padded_count += 1
        else:
            print(f"  Skipped: {img_path.name} (already correct size)")
    
    print("\n" + "=" * 60)
    print(f"Padding complete!")
    print(f"Padded {padded_count} images")
    print(f"All {num_images} images are now {max_width} x {max_height}")
    print("=" * 60)

if __name__ == '__main__':
    main()

