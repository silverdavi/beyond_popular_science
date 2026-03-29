#!/bin/bash
#
# Prepare KDP digital (eBook) cover image.
# Fast — just compiles the cover tex and converts to JPEG. ~10 seconds.
#
# Output:
#   kdp/cover_ebook.jpg  (1600 × 2560, JPEG, RGB, 1.6:1 ratio)
#
# Usage:
#   bash kdp/prepare_kdp_digital.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

KDP_EBOOK_COVER="kdp/cover_ebook.jpg"

echo "═══════════════════════════════════════════"
echo "  KDP DIGITAL — eBook Cover"
echo "═══════════════════════════════════════════"
echo ""

# ── Compile eBook cover ──────────────────────────────────────────────────

echo "[compile] Compiling eBook cover..."

cd kdp
lualatex --interaction=nonstopmode cover_ebook.tex > /dev/null 2>&1
cd "$PROJECT_ROOT"

if [ ! -f "kdp/cover_ebook.pdf" ]; then
    echo "[error] eBook cover compilation failed. Run manually:"
    echo "   cd kdp && lualatex cover_ebook.tex"
    exit 1
fi

# ── Convert to JPEG at 1600 × 2560 ──────────────────────────────────────

echo "[convert]  Converting to JPEG (1600 × 2560)..."

gs -q -dNOPAUSE -dBATCH -sDEVICE=jpeg -dJPEGQ=97 \
   -r256 \
   -sOutputFile="$KDP_EBOOK_COVER" \
   kdp/cover_ebook.pdf

# ── Verify ───────────────────────────────────────────────────────────────

EBOOK_SIZE=$(du -h "$KDP_EBOOK_COVER" | cut -f1)

if command -v sips &>/dev/null; then
    W=$(sips -g pixelWidth "$KDP_EBOOK_COVER" 2>/dev/null | tail -1 | awk '{print $2}')
    H=$(sips -g pixelHeight "$KDP_EBOOK_COVER" 2>/dev/null | tail -1 | awk '{print $2}')
    echo "   [ok] $KDP_EBOOK_COVER  (${W}×${H}, $EBOOK_SIZE)"
else
    echo "   [ok] $KDP_EBOOK_COVER  ($EBOOK_SIZE)"
fi

echo ""
echo "  Upload this as your Kindle eBook cover image."
echo ""
