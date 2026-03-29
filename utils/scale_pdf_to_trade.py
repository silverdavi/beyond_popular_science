#!/usr/bin/env python3
"""
Scale PDF from 7x10" (executive) to 6.14x9.21" (US Trade).

Uses pikepdf for the transformation, which preserves ALL annotations
including hyperlinks, bookmarks, and figure tooltip widgets (accessibility).

Optionally centres margins by applying a per-page horizontal shift
to equalise inner/outer margins for digital reading.

Usage:
    python3 utils/scale_pdf_to_trade.py <input.pdf> [output.pdf] [--centre-margins]
"""

import argparse
import sys
from decimal import Decimal
from pathlib import Path

import pikepdf

# Page dimensions in points (1 inch = 72 pt)
ORIG_W_IN, ORIG_H_IN = 7.0, 10.0
TARG_W_IN, TARG_H_IN = 6.14, 9.21

ORIG_W = ORIG_W_IN * 72   # 504.0
ORIG_H = ORIG_H_IN * 72   # 720.0
TARG_W = TARG_W_IN * 72   # 442.08
TARG_H = TARG_H_IN * 72   # 663.12

SCALE = TARG_W / ORIG_W   # 0.877143

# Vertical centering: scaled content is shorter than target page
SCALED_H = ORIG_H * SCALE
Y_OFFSET = (TARG_H - SCALED_H) / 2.0

# Margin centering shift (executive has inner=0.875", outer=0.625", diff=0.25")
# After scaling: diff * SCALE / 2 * 72 = margin shift in pt
MARGIN_SHIFT_PT = (0.25 * SCALE / 2) * 72  # ≈ 7.9 pt


def scale_page(pdf, page_obj, x_shift=0.0):
    """Scale a single page from executive to trade size, preserving annotations."""
    p = pikepdf.Page(page_obj)
    p.contents_coalesce()

    old_contents = page_obj.get("/Contents")
    if old_contents is None:
        return

    old_data = old_contents.read_bytes()

    total_x_shift = x_shift
    cm_line = f"q {SCALE:.6f} 0 0 {SCALE:.6f} {total_x_shift:.4f} {Y_OFFSET:.4f} cm\n"
    new_data = cm_line.encode() + old_data + b"\nQ\n"

    page_obj["/Contents"] = pdf.make_stream(new_data)
    page_obj["/MediaBox"] = pikepdf.Array([0, 0, Decimal(str(TARG_W)), Decimal(str(TARG_H))])

    if "/CropBox" in page_obj:
        page_obj["/CropBox"] = pikepdf.Array([0, 0, Decimal(str(TARG_W)), Decimal(str(TARG_H))])
    if "/TrimBox" in page_obj:
        page_obj["/TrimBox"] = pikepdf.Array([0, 0, Decimal(str(TARG_W)), Decimal(str(TARG_H))])

    # Scale annotation rectangles
    annots = page_obj.get("/Annots")
    if annots is None:
        return
    for ann in annots:
        rect = ann.get("/Rect")
        if rect is None:
            continue
        r = [float(v) for v in rect]
        ann["/Rect"] = pikepdf.Array([
            Decimal(str(round(r[0] * SCALE + x_shift, 3))),
            Decimal(str(round(r[1] * SCALE + Y_OFFSET, 3))),
            Decimal(str(round(r[2] * SCALE + x_shift, 3))),
            Decimal(str(round(r[3] * SCALE + Y_OFFSET, 3))),
        ])


def main():
    parser = argparse.ArgumentParser(
        description="Scale 7x10\" PDF to 6.14x9.21\" US Trade size"
    )
    parser.add_argument("input", help="Source PDF (executive 7x10\")")
    parser.add_argument("output", nargs="?", default=None, help="Output PDF")
    parser.add_argument("--centre-margins", action="store_true",
                        help=f"Shift pages ±{MARGIN_SHIFT_PT:.1f}pt to equalise inner/outer margins")
    args = parser.parse_args()

    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_trade{input_path.suffix}"

    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    print(f"[scale] SCALING TO US TRADE ({TARG_W_IN}\" × {TARG_H_IN}\")")
    print(f"   Input:  {input_path.name}")
    print(f"   Output: {output_path.name}")
    print(f"   Scale:  {SCALE:.4f} ({SCALE*100:.1f}%)")
    if args.centre_margins:
        print(f"   Margin centering: ±{MARGIN_SHIFT_PT:.1f} pt")

    pdf = pikepdf.open(input_path)
    n_pages = len(pdf.pages)
    widgets_before = 0
    links_before = 0

    for page in pdf.pages:
        for ann in page.get("/Annots", []):
            st = str(ann.get("/Subtype", ""))
            if st == "/Widget":
                widgets_before += 1
            elif st == "/Link":
                links_before += 1

    print(f"   Pages:  {n_pages}")
    print(f"   Annotations: {links_before} links, {widgets_before} tooltips")
    print()

    for i, page_obj in enumerate(pdf.pages):
        x_shift = 0.0
        if args.centre_margins:
            # Even 0-indexed pages = odd 1-indexed (recto): shift right
            # Odd 0-indexed pages = even 1-indexed (verso): shift left
            x_shift = MARGIN_SHIFT_PT if (i % 2 == 0) else -MARGIN_SHIFT_PT
        scale_page(pdf, page_obj, x_shift)

        if (i + 1) % 100 == 0 or i == n_pages - 1:
            print(f"   Processed {i + 1}/{n_pages} pages", end="\r")

    print()

    pdf.save(output_path)
    pdf.close()

    # Verify
    check = pikepdf.open(output_path)
    widgets_after = 0
    links_after = 0
    for page in check.pages:
        for ann in page.get("/Annots", []):
            st = str(ann.get("/Subtype", ""))
            if st == "/Widget":
                widgets_after += 1
            elif st == "/Link":
                links_after += 1
    check.close()

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"[ok] {output_path.name} ({size_mb:.1f} MB)")
    print(f"   {links_after}/{links_before} links, {widgets_after}/{widgets_before} tooltips preserved")

    if links_after != links_before or widgets_after != widgets_before:
        lost = (links_before - links_after) + (widgets_before - widgets_after)
        print(f"   [warn]  {lost} annotation(s) lost!")
        sys.exit(1)


if __name__ == "__main__":
    main()
