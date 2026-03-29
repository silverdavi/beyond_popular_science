#!/usr/bin/env python3
"""
Convert FASTA file to a text file where row k contains the first k base pairs.
"""

def fasta_to_growing_rows(input_fasta, output_txt):
    """
    Read FASTA file and create output where row k has the NEXT k base pairs.
    Row 1: bp1
    Row 2: bp2bp3  
    Row 3: bp4bp5bp6
    etc.
    
    Parameters:
    -----------
    input_fasta : str
        Path to input FASTA file
    output_txt : str
        Path to output text file
    """
    # Read FASTA file
    with open(input_fasta, 'r') as f:
        lines = f.readlines()
    
    # Extract sequence (skip header lines starting with '>')
    sequence = ""
    for line in lines:
        line = line.strip()
        if not line.startswith('>') and line:
            sequence += line
    
    print(f"Total sequence length: {len(sequence)} bp")
    
    # Calculate how many rows we can make
    # Row k needs k bp, total = 1+2+3+...+n = n(n+1)/2
    # Solve for n: n(n+1)/2 <= len(sequence)
    n = int((-1 + (1 + 8*len(sequence))**0.5) / 2)
    total_bp_used = n * (n + 1) // 2
    
    print(f"Will create {n} rows using {total_bp_used} bp")
    
    # Create output file with growing rows
    position = 0
    with open(output_txt, 'w') as f:
        for k in range(1, n + 1):
            # Row k gets the next k base pairs
            row_sequence = sequence[position:position + k]
            f.write(row_sequence + '\n')
            position += k
    
    print(f"Created {output_txt} with {n} rows")
    print(f"Row 1: {sequence[0:1]} (bp 1)")
    print(f"Row 2: {sequence[1:3]} (bp 2-3)")
    print(f"Row 3: {sequence[3:6]} (bp 4-6)")
    print(f"...")
    print(f"Row {n}: {sequence[total_bp_used-n:total_bp_used]} (bp {total_bp_used-n+1}-{total_bp_used})")

if __name__ == '__main__':
    input_file = 'ZFT.fasta'
    output_file = 'ZFT_growing.txt'
    
    fasta_to_growing_rows(input_file, output_file)

