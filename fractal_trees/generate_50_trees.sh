#!/bin/bash

# Generate 50 variations of the fractal tree

for i in {1..50}
do
    echo "Generating tree $i..."
    
    # Set a different random seed for each tree by modifying the LaTeX file
    # Use current timestamp + iteration number as seed
    SEED=$(($(date +%s) + $i))
    
    # Create a temporary LaTeX file with the new seed
    sed "s/\\\\begin{tikzpicture}\[scale=5\]/\\\\pgfmathsetseed{$SEED}\\n\\\\begin{tikzpicture}[scale=5]/" trees_another.tex > trees_another_temp.tex
    
    # Compile the temporary LaTeX file
    pdflatex -interaction=batchmode trees_another_temp.tex > /dev/null 2>&1
    
    # Convert to PNG at 600 DPI and move to tree_variations folder
    pdftocairo -png -r 600 trees_another_temp.pdf trees_another_temp
    mv trees_another_temp-1.png tree_variations/${i}.png
    
    echo "  -> Saved as tree_variations/${i}.png"
done

echo ""
echo "===================================================="
echo "Successfully generated 50 tree variations!"
echo "===================================================="

# Clean up LaTeX auxiliary files
rm -f trees_another_temp.* trees_another.aux trees_another.log

# Show file sizes
echo ""
echo "Generated files:"
ls -lh tree_variations/ | head -5
echo "..."
echo "Total: $(ls tree_variations/*.png | wc -l) PNG files"

