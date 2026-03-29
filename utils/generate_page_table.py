#!/usr/bin/env python3
"""
Generate detailed CSV table of page structure from compiled PDF.
Maps each page to chapter, section type, and position within section.
"""

import csv
import re
import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess

def parse_aux_file(aux_file):
    """Parse .aux file to extract page references and structure."""
    if not Path(aux_file).exists():
        return {}
    
    page_refs = {}
    
    try:
        with open(aux_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract chapter labels and page numbers
        # Format: \newlabel{ch:chaptername}{{number}{page}...}
        chapter_matches = re.findall(r'\\newlabel\{ch:([^}]+)\}\{\{(\d+)\}\{(\d+)\}', content)
        for label, chapter_num, page_num in chapter_matches:
            page_refs[int(page_num)] = {
                'type': 'chapter_start',
                'chapter': int(chapter_num),
                'label': label
            }
        
        # Extract other structural references
        # Format: \newlabel{...}{{...}{page}...}
        all_refs = re.findall(r'\\newlabel\{([^}]+)\}\{[^{]*\{(\d+)\}', content)
        for label, page_num in all_refs:
            if label not in [f'ch:{ref["label"]}' for ref in page_refs.values() if 'label' in ref]:
                page_refs[int(page_num)] = page_refs.get(int(page_num), {})
                page_refs[int(page_num)]['references'] = page_refs[int(page_num)].get('references', [])
                page_refs[int(page_num)]['references'].append(label)
    
    except Exception as e:
        print(f"[warn]  Could not parse aux file: {e}")
    
    return page_refs

def parse_toc_file(toc_file):
    """Parse .toc file to extract chapter titles and page numbers."""
    if not Path(toc_file).exists():
        return {}
    
    toc_info = {}
    
    try:
        with open(toc_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract chapter entries from ToC
        # Format: \contentsline {chapter}{\numberline {N}Title \\ {...}}{page}{...}
        chapter_matches = re.findall(r'\\contentsline\s*\{chapter\}\{\\numberline\s*\{(\d+)\}([^}]+).*?\}\{(\d+)\}', content)
        
        for chapter_num, title, page_num in chapter_matches:
            # Clean up the title
            title = re.sub(r'\\\\.*$', '', title).strip()
            title = re.sub(r'\s+', ' ', title)
            
            toc_info[int(page_num)] = {
                'chapter': int(chapter_num),
                'title': title,
                'type': 'chapter_start'
            }
    
    except Exception as e:
        print(f"[warn]  Could not parse toc file: {e}")
    
    return toc_info

def analyze_log_file(log_file):
    """Analyze log file for ACTUAL page structure and file inclusions."""
    if not Path(log_file).exists():
        return {}
    
    page_to_content = {}
    current_page = 1
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Track file inclusions and page breaks
        current_files = []  # Stack of currently open files
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Track page numbers
            page_match = re.search(r'^\[(\d+)', line)
            if page_match:
                current_page = int(page_match.group(1))
            
            # Track file openings - look for file paths in parentheses
            file_open_match = re.search(r'\(\.?/?(\d+_[^/]+/[\w]+\.tex)', line)
            if file_open_match:
                file_path = file_open_match.group(1)
                current_files.append(file_path)
                
                # Parse chapter and section from file path
                path_parts = file_path.split('/')
                if len(path_parts) == 2:
                    chapter_dir = path_parts[0]
                    filename = path_parts[1].replace('.tex', '')
                    
                    # Extract chapter number and name
                    chapter_match = re.match(r'(\d+)_(.+)', chapter_dir)
                    if chapter_match:
                        chapter_num = int(chapter_match.group(1))
                        chapter_name = chapter_match.group(2)
                        
                        # Map filename to section type
                        section_map = {
                            'title': 'title',
                            'summary': 'summary', 
                            'topicmap': 'topicmap',
                            'quote': 'quote',
                            'historical': 'historical',
                            'main': 'main',
                            'technical': 'technical',
                            'exercises': 'exercises',
                            'imagefigure': 'imagefigure',
                            'joke': 'joke',
                            'cartoon': 'cartoon',
                            'sidenote': 'sidenote'
                        }
                        
                        section_type = section_map.get(filename, filename)
                        
                        # Associate this content with current page
                        page_to_content[current_page] = {
                            'chapter': chapter_num,
                            'chapter_name': chapter_name,
                            'section': section_type,
                            'file_path': file_path
                        }
            
            # Track file closings
            if line == ')':
                if current_files:
                    current_files.pop()
    
    except Exception as e:
        print(f"[warn]  Could not parse log file: {e}")
    
    return page_to_content

def get_pdf_page_count(pdf_file):
    """Get total page count from PDF using pdfinfo or similar."""
    if not Path(pdf_file).exists():
        return None
    
    try:
        # Try pdfinfo first
        result = subprocess.run(['pdfinfo', pdf_file], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'Pages:' in line:
                    return int(line.split(':')[1].strip())
    except:
        pass
    
    try:
        # Try pdfplumber as fallback
        import pdfplumber
        with pdfplumber.open(pdf_file) as pdf:
            return len(pdf.pages)
    except:
        pass
    
    return None

def generate_page_table(pdf_file, base_name):
    """Generate comprehensive page table CSV."""
    
    print("[info] GENERATING PAGE STRUCTURE TABLE")
    print("=" * 50)
    
    # Parse auxiliary files
    aux_file = f'{base_name}.aux'
    toc_file = f'{base_name}.toc'
    log_file = f'{base_name}.log'
    
    print(f"[file] Parsing auxiliary files...")
    aux_data = parse_aux_file(aux_file)
    toc_data = parse_toc_file(toc_file)
    log_data = analyze_log_file(log_file)
    
    print(f"  - Aux references: {len(aux_data)}")
    print(f"  - ToC entries: {len(toc_data)}")
    print(f"  - Log page mappings: {len(log_data)}")
    
    # Get total page count
    total_pages = None
    if pdf_file:
        total_pages = get_pdf_page_count(pdf_file)
    
    if total_pages:
        print(f"[info] PDF contains {total_pages} pages")
    else:
        # Estimate from log data or aux data
        max_log_page = max(log_data.keys()) if log_data else 0
        max_aux_page = max(aux_data.keys()) if aux_data else 0
        max_toc_page = max(toc_data.keys()) if toc_data else 0
        
        total_pages = max(max_log_page, max_aux_page, max_toc_page, 600)
        print(f"[info] Estimated {total_pages} pages (from auxiliary files)")
    
    # Generate page mapping based on ACTUAL compilation reality
    page_table = []
    
    # Track chapter progression and section changes
    current_chapter = 0
    current_chapter_name = ""
    current_section = "unknown"
    chapter_start_page = 1
    section_start_page = 1
    
    for page_num in range(1, total_pages + 1):
        
        # Check if this page has actual data from compilation
        actual_chapter = current_chapter
        actual_chapter_name = current_chapter_name
        actual_section = current_section
        
        # Update from ToC data (most reliable for chapter starts)
        if page_num in toc_data:
            actual_chapter = toc_data[page_num]['chapter']
            actual_chapter_name = toc_data[page_num]['title']
            actual_section = "title_page"  # ToC entries mark title pages
            if actual_chapter != current_chapter:
                chapter_start_page = page_num
                current_chapter = actual_chapter
                current_chapter_name = actual_chapter_name
            section_start_page = page_num
            current_section = actual_section
        
        # Update from log data (shows actual file inclusions)
        elif page_num in log_data:
            log_entry = log_data[page_num]
            actual_chapter = log_entry['chapter']
            actual_chapter_name = log_entry['chapter_name']
            actual_section = log_entry['section']
            
            # Check if chapter changed
            if actual_chapter != current_chapter:
                chapter_start_page = page_num
                current_chapter = actual_chapter
                current_chapter_name = actual_chapter_name
            
            # Check if section changed
            if actual_section != current_section:
                section_start_page = page_num
                current_section = actual_section
        
        # Update from aux data
        elif page_num in aux_data:
            if aux_data[page_num].get('type') == 'chapter_start':
                actual_chapter = aux_data[page_num]['chapter']
                actual_chapter_name = aux_data[page_num].get('label', '')
                chapter_start_page = page_num
                current_chapter = actual_chapter
                current_chapter_name = actual_chapter_name
        
        # Calculate positions
        page_in_chapter = page_num - chapter_start_page + 1
        page_in_section = page_num - section_start_page + 1
        
        # Check for layout warnings (from page flow analysis)
        has_warning = False
        warning_type = ""
        
        page_table.append({
            'page': page_num,
            'chapter': actual_chapter if actual_chapter > 0 else current_chapter,
            'chapter_name': actual_chapter_name or current_chapter_name,
            'section': actual_section,
            'page_in_chapter': page_in_chapter,
            'page_in_section': page_in_section,
            'has_warning': has_warning,
            'warning_type': warning_type
        })
    
    # Save to CSV
    csv_file = f'{base_name}_page_structure.csv'
    
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['page', 'chapter', 'chapter_name', 'section', 'page_in_chapter', 'page_in_section', 'has_warning', 'warning_type']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(page_table)
        
        print(f"[ok] Page structure table saved: {csv_file}")
        
        # Show summary statistics
        sections = {}
        for row in page_table:
            section = row['section']
            sections[section] = sections.get(section, 0) + 1
        
        print(f"\n[info] SECTION BREAKDOWN:")
        for section, count in sorted(sections.items(), key=lambda x: x[1], reverse=True):
            print(f"  {section:12s}: {count:3d} pages")
        
        warnings = sum(1 for row in page_table if row['has_warning'])
        if warnings:
            print(f"\n[warn]  Pages with warnings: {warnings}")
        
        return csv_file
        
    except Exception as e:
        print(f"[error] Could not save CSV file: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_page_table.py <base_name_or_pdf_file> [base_name]")
        print("Examples:")
        print("  python generate_page_table.py main.pdf main")
        print("  python generate_page_table.py main  # Uses aux/log files only")
        sys.exit(1)
    
    input_arg = sys.argv[1]
    
    # Determine if input is PDF file or base name
    if input_arg.endswith('.pdf'):
        pdf_file = input_arg
        base_name = sys.argv[2] if len(sys.argv) > 2 else Path(pdf_file).stem
        
        if not Path(pdf_file).exists():
            print(f"[warn]  PDF file not found: {pdf_file}")
            print(f"   Will analyze using auxiliary files only...")
            pdf_file = None
    else:
        # Input is base name
        base_name = input_arg
        pdf_file = f'{base_name}.pdf'
        
        if not Path(pdf_file).exists():
            print(f"[warn]  PDF file not found: {pdf_file}")
            print(f"   Will analyze using auxiliary files only...")
            pdf_file = None
    
    csv_file = generate_page_table(pdf_file, base_name)
    
    if csv_file:
        print(f"\n[info] SUCCESS: Detailed page structure saved to {csv_file}")
        print(f"   Use this CSV to analyze page flow, identify empty pages,")
        print(f"   and optimize chapter layouts for your 8-page target structure.")
    else:
        print("[error] Failed to generate page structure table")
        sys.exit(1)

if __name__ == "__main__":
    main()
