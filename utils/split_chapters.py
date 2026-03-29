#!/usr/bin/env python3
"""
Split the compiled book PDF into individual chapter PDFs.

Produces 52 files:
  - 00_FrontMatter.pdf          (front matter: halftitle, title, copyright, intro, TOC, prologue)
  - 01_<Name>.pdf .. 50_<Name>.pdf  (9 pages each, no blank separator)
  - 51_BackMatter.pdf           (subject index + biographical reference)

Requires: qpdf (brew install qpdf)

Usage:
  python3 utils/split_chapters.py main_6.14x9.21_trade.pdf
  python3 utils/split_chapters.py main.pdf -o chapters/
"""

import subprocess
import sys
import os
import re
from pathlib import Path

# The front matter occupies the first 20 PDF pages (roman numerals).
# Arabic page 1 = PDF page 21 (1-based).
FRONT_MATTER_PAGES = 20
CHAPTER_CONTENT_PAGES = 9
CHAPTER_TOTAL_PAGES = 10  # 9 content + 1 blank separator


def get_chapter_dirs(main_tex='main.tex'):
    """Parse main.tex to get ordered list of chapter directory names."""
    with open(main_tex, 'r', encoding='utf-8') as f:
        content = f.read()

    dirs = []
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('%') and '\\inputstory{' in line:
            match = re.search(r'\\inputstory\{([^}]+)\}', line)
            if match:
                dirs.append(match.group(1))
    return dirs


def read_title(chapter_dir):
    """Read title.tex from a chapter directory."""
    title_path = os.path.join(chapter_dir, 'title.tex')
    if os.path.exists(title_path):
        with open(title_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return chapter_dir


def sanitize_filename(name):
    """Make a string safe for use as a filename."""
    # Remove LaTeX commands
    name = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', name)
    name = re.sub(r'\\[a-zA-Z]+', '', name)
    name = re.sub(r'[${}\\]', '', name)
    # Replace unsafe characters
    name = re.sub(r'[/:*?"<>|]', '', name)
    # Collapse whitespace to underscores
    name = re.sub(r'\s+', '_', name.strip())
    # Remove trailing underscores
    name = name.strip('_')
    return name


def split_pdf(input_pdf, output_dir='chapters_split', main_tex='main.tex'):
    """Split the book PDF into individual chapter files."""

    input_path = Path(input_pdf)
    if not input_path.exists():
        print(f"[error] Error: {input_pdf} not found")
        return False

    # Get total page count
    result = subprocess.run(
        ['qpdf', '--show-npages', str(input_path)],
        capture_output=True, text=True
    )
    total_pages = int(result.stdout.strip())

    # Get chapter directories
    chapter_dirs = get_chapter_dirs(main_tex)
    num_chapters = len(chapter_dirs)

    print(f"[info] SPLITTING BOOK INTO INDIVIDUAL CHAPTERS")
    print("=" * 50)
    print(f"[file] Input:    {input_path.name} ({total_pages} pages)")
    print(f"[info] Chapters: {num_chapters}")
    print(f"[dir] Output:   {output_dir}/")
    print()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    files_created = []

    # --- Front matter ---
    front_file = os.path.join(output_dir, '00_FrontMatter.pdf')
    _extract(input_path, 1, FRONT_MATTER_PAGES, front_file)
    files_created.append(front_file)
    print(f"  [ok] 00_FrontMatter.pdf  (pages 1–{FRONT_MATTER_PAGES})")

    # --- Chapters 1-N ---
    for i, chapter_dir in enumerate(chapter_dirs):
        chapter_num = i + 1
        title = read_title(chapter_dir)
        safe_title = sanitize_filename(title)

        # Chapter 1 starts right after front matter (no leading blank).
        # Chapters 2+ have a blank separator page before them that we skip.
        first_page = FRONT_MATTER_PAGES + (i * CHAPTER_TOTAL_PAGES) + 1
        last_page = first_page + CHAPTER_CONTENT_PAGES - 1

        filename = f"{chapter_num:02d}_{safe_title}.pdf"
        out_file = os.path.join(output_dir, filename)
        _extract(input_path, first_page, last_page, out_file)
        files_created.append(out_file)
        print(f"  [ok] {filename}  (pages {first_page}–{last_page})")

    # --- Back matter (subject index + biographical reference) ---
    back_start = FRONT_MATTER_PAGES + (num_chapters * CHAPTER_TOTAL_PAGES) + 1
    if back_start <= total_pages:
        back_file = os.path.join(output_dir, '51_BackMatter.pdf')
        _extract(input_path, back_start, total_pages, back_file)
        files_created.append(back_file)
        print(f"  [ok] 51_BackMatter.pdf  (pages {back_start}–{total_pages})")

    print()
    print(f"[ok] Split complete: {len(files_created)} files in {output_dir}/")
    return files_created


def _extract(input_pdf, first_page, last_page, output_file):
    """Extract a page range from a PDF using qpdf."""
    subprocess.run(
        ['qpdf', str(input_pdf),
         '--pages', str(input_pdf), f'{first_page}-{last_page}', '--',
         output_file],
        check=True, capture_output=True
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Split book PDF into individual chapter PDFs')
    parser.add_argument('pdf', help='Input PDF file')
    parser.add_argument('-o', '--output', default='chapters_split',
                        help='Output directory (default: chapters_split)')
    parser.add_argument('-m', '--main-tex', default='main.tex',
                        help='Path to main.tex (default: main.tex)')
    args = parser.parse_args()

    files = split_pdf(args.pdf, args.output, args.main_tex)
    sys.exit(0 if files else 1)


if __name__ == "__main__":
    main()
