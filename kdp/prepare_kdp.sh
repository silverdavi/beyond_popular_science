#!/bin/bash
#
# Prepare KDP-ready files (interior + cover) from the Unpopular Science edition.
#
# What this does:
#   1. Post-processes the manuscript PDF:
#      - Strips PDF/A metadata that confuses KDP's validator
#      - Removes non-printable annotations (hyperlinks, bookmarks)
#      - Forces full font embedding
#      - Normalizes page boxes (MediaBox/TrimBox/BleedBox)
#   2. Compiles the KDP cover with exact dimensions:
#      - 15.486" x 10.250" (7" x 10" trim, 1.236" spine, 0.125" bleed)
#
# Prerequisites:
#   brew install ghostscript
#   TeX Live with lualatex
#
# Input:
#   main_unpopular_science.pdf  (from utils/compile_both_editions.py)
#
# Output:
#   kdp/unpopular_science_kdp_interior.pdf
#   kdp/cover_kdp.pdf
#
# Usage:
#   bash kdp/prepare_kdp.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

MANUSCRIPT="main_unpopular_science.pdf"
KDP_INTERIOR="kdp/unpopular_science_kdp_interior.pdf"
KDP_COVER="kdp/cover_kdp.pdf"

echo "═══════════════════════════════════════════"
echo "  KDP FILE PREPARATION"
echo "═══════════════════════════════════════════"
echo ""

# ── Step 0: Check prerequisites ──────────────────────────────────────────

if [ ! -f "$MANUSCRIPT" ]; then
    echo "[error] $MANUSCRIPT not found."
    echo "   Run: python3 utils/compile_both_editions.py"
    exit 1
fi

if ! command -v gs &>/dev/null; then
    echo "[error] Ghostscript not found. Install with: brew install ghostscript"
    exit 1
fi

# ── Step 1: Post-process manuscript for KDP ──────────────────────────────

echo "[info] Post-processing manuscript..."
echo "   Stripping PDF/A metadata, flattening annotations, embedding fonts"

gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.7 \
   -dEmbedAllFonts=true \
   -dSubsetFonts=true \
   -dPrinted=true \
   -dHaveTransparency=false \
   -dAutoRotatePages=/None \
   -dDetectDuplicateImages=true \
   -dCompressFonts=true \
   -dPDFSETTINGS=/prepress \
   -sOutputFile="$KDP_INTERIOR" \
   "$MANUSCRIPT"

INTERIOR_SIZE=$(du -h "$KDP_INTERIOR" | cut -f1)
echo "   [ok] $KDP_INTERIOR  ($INTERIOR_SIZE)"

# ── Step 2: Compile KDP cover ────────────────────────────────────────────

echo ""
echo "[compile] Compiling KDP cover (15.486\" × 10.250\")..."

cd kdp
lualatex --interaction=nonstopmode cover_kdp.tex > /dev/null 2>&1
lualatex --interaction=nonstopmode cover_kdp.tex > /dev/null 2>&1
cd "$PROJECT_ROOT"

if [ ! -f "$KDP_COVER" ]; then
    echo "[error] Cover compilation failed. Run manually for details:"
    echo "   cd kdp && lualatex cover_kdp.tex"
    exit 1
fi

# Post-process cover for font embedding too
gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.7 \
   -dEmbedAllFonts=true \
   -dSubsetFonts=true \
   -dAutoRotatePages=/None \
   -dPDFSETTINGS=/prepress \
   -sOutputFile="kdp/cover_kdp_embedded.pdf" \
   "$KDP_COVER"

mv "kdp/cover_kdp_embedded.pdf" "$KDP_COVER"

COVER_SIZE=$(du -h "$KDP_COVER" | cut -f1)
echo "   [ok] $KDP_COVER  ($COVER_SIZE)"

# ── Step 3: Verify dimensions ────────────────────────────────────────────

echo ""
echo "[verify] Verifying PDF dimensions..."

if command -v pdfinfo &>/dev/null; then
    INTERIOR_DIMS=$(pdfinfo "$KDP_INTERIOR" 2>/dev/null | grep "Page size" | head -1)
    COVER_DIMS=$(pdfinfo "$KDP_COVER" 2>/dev/null | grep "Page size" | head -1)
    echo "   Interior: $INTERIOR_DIMS"
    echo "   Cover:    $COVER_DIMS"
else
    echo "   (install poppler for dimension verification: brew install poppler)"
fi


# ── Done ─────────────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════"
echo "  [ok] KDP FILES READY"
echo "═══════════════════════════════════════════"
echo ""
echo "  Interior: $KDP_INTERIOR"
echo "  Cover:    $KDP_COVER"
echo ""
echo "  Upload these files to KDP."
echo ""
echo "  Notes:"
echo "  • If KDP still flags gutter issues, specific pages may"
echo "    have wide equations or images extending into margins."
echo "    Check the flagged pages manually."
echo "  • Hyperlinks have been flattened (text remains, links removed)."
echo "  • PDF/A metadata has been stripped."
echo ""
