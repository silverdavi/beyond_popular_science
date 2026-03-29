#!/usr/bin/env python3
"""
Compile the Beyond Popular Science edition (Open Book Publishers).

Temporarily ensures name.tex and titlepage.tex match the BPS edition,
compiles with compile_realtime.py (two lualatex passes), and saves output.

The copyright page is read directly from copyright.tex (source of truth).

Usage:
    python3 utils/compile_both_editions.py
"""

import os
import sys
import shutil
import subprocess
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Edition definitions — only BPS for now
# ---------------------------------------------------------------------------
EDITIONS = [
    {
        "name": "Beyond Popular Science",
        "slug": "beyond_popular_science",
        "booktitle": "Beyond Popular Science",
        "publisher": "Open Book Publishers",
        # copyright.tex is the source of truth — not overwritten by this script
        "copyright_tex": None,
    },
    # Unpopular Science (Kernel Keys Press) edition disabled for now
    # {
    #     "name": "Unpopular Science",
    #     "slug": "unpopular_science",
    #     "booktitle": "Unpopular Science",
    #     "publisher": "Kernel Keys Press",
    #     "copyright_tex": ...,
    # },
]

# Files that differ between editions
MODIFIED_FILES = ["name.tex", "titlepage.tex"]  # copyright.tex is now source of truth

TEX_FILE = "main.tex"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def backup_files():
    """Save originals before modification."""
    for f in MODIFIED_FILES:
        bak = f + ".edition_bak"
        shutil.copy2(f, bak)
    print("  [info] Backed up: " + ", ".join(MODIFIED_FILES))


def restore_files():
    """Restore originals from backups."""
    restored = []
    for f in MODIFIED_FILES:
        bak = f + ".edition_bak"
        if os.path.exists(bak):
            shutil.move(bak, f)
            restored.append(f)
    if restored:
        print("  [..] Restored: " + ", ".join(restored))


def apply_edition(edition):
    """Rewrite name.tex, copyright.tex, and titlepage.tex for this edition."""

    # --- name.tex ---
    with open("name.tex", "w") as fh:
        fh.write("% Single source of truth for the book title.\n")
        fh.write("% Change the title here and it propagates everywhere:\n")
        fh.write("% main, cover, titlepage, halftitle, copyright, headers.\n")
        fh.write(f"\\newcommand{{\\booktitle}}{{{edition['booktitle']}}}\n")

    # --- copyright.tex — only overwrite if edition defines its own content ---
    if edition["copyright_tex"] is not None:
        with open("copyright.tex", "w") as fh:
            fh.write(edition["copyright_tex"])
    else:
        print("  [file] copyright.tex: using source file as-is")

    # --- titlepage.tex ---
    with open("titlepage.tex", "r") as fh:
        text = fh.read()
    # Replace the publisher text inside \textsc{...}
    text = re.sub(
        r'(\\textcolor\{black!60\}\{\\textsc\{)[^}]*(\}\})',
        rf'\g<1>{edition["publisher"]}\g<2>',
        text,
    )
    with open("titlepage.tex", "w") as fh:
        fh.write(text)

    print(f"  [info] Applied: title=\"{edition['booktitle']}\", "
          f"publisher={edition['publisher']}")


def compile_edition(edition):
    """Compile one edition and save the output PDF."""
    slug = edition["slug"]
    output_pdf = f"main_{slug}.pdf"

    print(f"\n{'=' * 60}")
    print(f"  [info] EDITION: {edition['name']}")
    print(f"{'=' * 60}")

    apply_edition(edition)

    # Run compile_realtime.py (which does two lualatex passes + post-processing)
    result = subprocess.run(
        [sys.executable, "utils/compile_realtime.py", TEX_FILE],
        cwd=".",
    )

    if result.returncode != 0:
        print(f"\n  [error] Compilation FAILED for \"{edition['name']}\"")
        return False

    base = os.path.splitext(TEX_FILE)[0]
    src_pdf = f"{base}.pdf"

    if not os.path.exists(src_pdf):
        print(f"\n  [error] Expected PDF not found: {src_pdf}")
        return False

    # Save with edition-specific name
    shutil.copy2(src_pdf, output_pdf)
    size_mb = os.path.getsize(output_pdf) / (1024 * 1024)
    print(f"\n  [ok] Saved: {output_pdf}  ({size_mb:.1f} MB)")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Must run from project root
    if not os.path.exists(TEX_FILE):
        print("[error] Run from the project root (where main.tex is).")
        sys.exit(1)

    start = datetime.now()

    print("[info] SINGLE-EDITION COMPILATION (Beyond Popular Science)")
    print("=" * 60)
    print(f"  Started:  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    for ed in EDITIONS:
        print(f"  • \"{ed['name']}\"  →  main_{ed['slug']}.pdf")
    print()

    backup_files()

    results = []
    try:
        for edition in EDITIONS:
            ok = compile_edition(edition)
            results.append((edition, ok))
    finally:
        # Always restore, even on crash
        print()
        restore_files()

    # Summary
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'=' * 60}")
    print(f"  SUMMARY  ({elapsed:.0f}s total)")
    print(f"{'=' * 60}")
    for edition, ok in results:
        icon = "[ok]" if ok else "[error]"
        pdf = f"main_{edition['slug']}.pdf"
        if ok and os.path.exists(pdf):
            size = os.path.getsize(pdf) / (1024 * 1024)
            print(f"  {icon} {edition['name']:30s}  {pdf}  ({size:.1f} MB)")
        else:
            print(f"  {icon} {edition['name']:30s}  FAILED")

    all_ok = all(ok for _, ok in results)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
