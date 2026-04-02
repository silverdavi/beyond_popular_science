#!/bin/bash
#
# Publish both book editions as a GitHub release (tagged "latest").
# Produces print + digital + preview editions from the compiled source PDFs.
#
# Pipeline:
#   1. lualatex  — compile default (print margins, 7"×10")
#                  → main_beyond_popular_science.pdf
#   2. lualatex  — compile digital (\digitaltrue, centred margins, 7"×10")
#                  → BPS_v*_digital_*.pdf
#   3. gs        — uniform-scale print to US Trade 6.14"×9.21"
#                  → BPS_v*_prePDFX_USTrade_*.pdf
#   4. [manual]  — Acrobat: Convert to PDF/X-1a (Coated FOGRA39)
#                  → BPS_v*_PDFX_USTrade_*.pdf
#   5. gs        — compress digital → preview
#
# Prerequisites:
#   brew install gh ghostscript
#   gh auth login
#
# Usage:
#   ./release_pdf.sh

set -e

# ---------------------------------------------------------------------------
# Version & datestamp
# ---------------------------------------------------------------------------
VERSION="1.09"
DATESTAMP=$(date '+%Y%m%d')
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

# ---------------------------------------------------------------------------
# Source files (compiled by utils/compile_both_editions.py)
# ---------------------------------------------------------------------------
BPS_EXECUTIVE="main_beyond_popular_science.pdf"     # Beyond Popular Science, 7×10
US_EXECUTIVE="main_unpopular_science.pdf"           # Unpopular Science, 7×10
COVER_FILE="cover/cover_refined.pdf"

# Intermediate (for chapter splitting)
US_TRADE="main_unpopular_science_trade.pdf"

# Release file names — Beyond Popular Science
REL_BPS_DIGITAL="BPS_v${VERSION}_digital_${DATESTAMP}.pdf"   # Centred margins, RGB, interactive
REL_BPS_PRE_PRINT="BPS_v${VERSION}_prePDFX_USTrade_${DATESTAMP}.pdf" # GS-scaled, pre-Acrobat
REL_BPS_PRINT="BPS_v${VERSION}_PDFX_USTrade_${DATESTAMP}.pdf"       # Final PDF/X-1a via Acrobat
REL_BPS_PREVIEW="BPS_v${VERSION}_preview_${DATESTAMP}.pdf"   # Compressed for quick review
REL_BPS_MAIN="main.pdf"                                     # Alias → digital (stable URL)

# Release file names — Unpopular Science
REL_US_EXEC="US_v${VERSION}_executive_${DATESTAMP}.pdf"
REL_US_PREVIEW="US_v${VERSION}_preview_${DATESTAMP}.pdf"

REPO="silverdavi/beyond_popular_science"
TAG="latest"

VENV_PY="venv/bin/python3"

echo "[info] RELEASE SCRIPT — v${VERSION} (${DATESTAMP})"
echo "==========================================="
echo ""

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
for f in "$COVER_FILE"; do
  if [ ! -f "$f" ]; then
    echo "[error] Error: $f not found."
    exit 1
  fi
done

if [ ! -f "main.tex" ]; then
  echo "[error] Error: main.tex not found. Run from project root."
  exit 1
fi

if ! command -v gh &> /dev/null; then
  echo "[error] Error: GitHub CLI (gh) is not installed."
  echo "   Install it with: brew install gh"
  exit 1
fi

# ---------------------------------------------------------------------------
# BPS: Compile default (print margins) → main_beyond_popular_science.pdf
# ---------------------------------------------------------------------------
echo "[compile] BPS: Compiling default edition (print margins, 7\"×10\")..."
"$VENV_PY" utils/compile_realtime.py main.tex
cp main.pdf "$BPS_EXECUTIVE"
echo "   [ok] $BPS_EXECUTIVE ($(du -h "$BPS_EXECUTIVE" | cut -f1))"

# ---------------------------------------------------------------------------
# BPS: DIGITAL edition — recompile with centred margins
# Flips \digitalfalse → \digitaltrue in preamble.tex, compiles, flips back
# ---------------------------------------------------------------------------
echo ""
echo "[compile] BPS: Compiling DIGITAL edition (centred margins, 7\"×10\")..."
sed -i '' 's/\\digitalfalse/\\digitaltrue/' preamble.tex
"$VENV_PY" utils/compile_realtime.py main.tex || { sed -i '' 's/\\digitaltrue/\\digitalfalse/' preamble.tex; exit 1; }
sed -i '' 's/\\digitaltrue/\\digitalfalse/' preamble.tex
cp main.pdf "$REL_BPS_DIGITAL"
echo "   [ok] $REL_BPS_DIGITAL ($(du -h "$REL_BPS_DIGITAL" | cut -f1))"

# ---------------------------------------------------------------------------
# PDF metadata (re-injected by GS via pdfmark since GS rewrites from scratch)
# ---------------------------------------------------------------------------
PDF_METADATA='
[ /Title (Beyond Popular Science)
  /Author (David H. Silver)
  /Subject (Fifty explorations at the boundary of mainstream science)
  /Keywords (science, physics, mathematics, cosmology, biology, popular science, ISBN 978-1-80511-879-4)
  /Creator (LuaLaTeX)
  /Producer (LuaLaTeX / Ghostscript)
  /DOCINFO pdfmark
'

# ---------------------------------------------------------------------------
# BPS: PRINT edition — GS uniform-scales to US Trade (no CMYK, no PDF/X)
# Acrobat handles PDF/X-1a conversion: Convert to PDF/X-1a (Coated FOGRA39)
# ---------------------------------------------------------------------------
echo ""
echo "[print]  BPS: Scaling to US Trade for print (pre-PDF/X)..."

TRADE_W=442.08  # 6.14" × 72
TRADE_H=663.12  # 9.21" × 72

gs -dBATCH -dNOPAUSE -dNOSAFER \
   -sDEVICE=pdfwrite \
   -dPDFSETTINGS=/prepress \
   -dAutoRotatePages=/None \
   -dDownsampleColorImages=false \
   -dDownsampleGrayImages=false \
   -dDownsampleMonoImages=false \
   -dEmbedAllFonts=true \
   -dSubsetFonts=true \
   -dFIXEDMEDIA \
   -dDEVICEWIDTHPOINTS=${TRADE_W} \
   -dDEVICEHEIGHTPOINTS=${TRADE_H} \
   -dPDFFitPage \
   -sOutputFile="$REL_BPS_PRE_PRINT" \
   -c "$PDF_METADATA" \
   -f "$BPS_EXECUTIVE"

echo "   [ok] $REL_BPS_PRE_PRINT ($(du -h "$REL_BPS_PRE_PRINT" | cut -f1))"
echo "   [warn]  Convert to PDF/X-1a in Acrobat: Preflight → Convert to PDF/X-1a (Coated FOGRA39)"
echo "   [warn]  Save as: $REL_BPS_PRINT"

# ---------------------------------------------------------------------------
# BPS: Preview (compressed via GS — tooltips lost here is acceptable)
# ---------------------------------------------------------------------------
echo ""
echo "[compress]  BPS: Generating preview (compressed)..."
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile="$REL_BPS_PREVIEW" \
   -c "$PDF_METADATA" \
   -f "$REL_BPS_DIGITAL"
echo "   [ok] $REL_BPS_PREVIEW ($(du -h "$REL_BPS_PREVIEW" | cut -f1))"

# Default download = digital edition
cp "$REL_BPS_DIGITAL" "$REL_BPS_MAIN"

# ---------------------------------------------------------------------------
# Unpopular Science — preview from executive
# ---------------------------------------------------------------------------
echo ""
echo "[compress]  US: Generating preview (compressed executive)..."
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile="$REL_US_PREVIEW" "$US_EXECUTIVE"
echo "   [ok] $(du -h "$REL_US_PREVIEW" | cut -f1)"

# ---------------------------------------------------------------------------
# Chapter splitting — from Unpopular Science (scale to trade first)
# ---------------------------------------------------------------------------
echo ""
echo "[scale] US: Scaling to trade for chapter splitting..."
if [ -f "$US_TRADE" ] && [ "$US_TRADE" -nt "$US_EXECUTIVE" ]; then
  echo "   Trade PDF is up to date."
else
  "$VENV_PY" utils/scale_pdf_to_trade.py "$US_EXECUTIVE" "$US_TRADE"
fi

echo ""
echo "[info] Splitting Unpopular Science into individual chapter PDFs..."
CHAPTERS_DIR="chapters_split"
python3 utils/split_chapters.py "$US_TRADE" -o "$CHAPTERS_DIR"

if [ ! -d "$CHAPTERS_DIR" ]; then
  echo "[error] Error: Chapter splitting failed"
  exit 1
fi

CHAPTER_COUNT=$(ls "$CHAPTERS_DIR"/*.pdf | wc -l | tr -d ' ')
echo "   [ok] $CHAPTER_COUNT chapter PDFs ready"

# ---------------------------------------------------------------------------
# Prepare release copies
# ---------------------------------------------------------------------------
echo ""
echo "[release] Preparing release files..."

cp "$REL_BPS_DIGITAL" "$REL_BPS_MAIN"
cp "$US_EXECUTIVE" "$REL_US_EXEC"

echo ""
echo "   Beyond Popular Science:"
echo "     [ok] $REL_BPS_MAIN (= digital, stable download URL)"
echo "     [ok] $REL_BPS_DIGITAL (digital, centred margins, interactive)"
[ -f "$REL_BPS_PRINT" ] && \
echo "     [ok] $REL_BPS_PRINT (PDF/X-1a, CMYK, US Trade — print-ready)"
echo "     [ok] $REL_BPS_PREVIEW (compressed preview)"
echo ""
echo "   Unpopular Science:"
echo "     [ok] $REL_US_EXEC (executive 7\"×10\")"
echo "     [ok] $REL_US_PREVIEW (compressed preview)"
echo ""
echo "   Shared:"
echo "     [ok] $COVER_FILE"
echo "     [ok] $CHAPTER_COUNT individual chapter PDFs"

# ---------------------------------------------------------------------------
# Upload to GitHub
# ---------------------------------------------------------------------------
echo ""
echo "[cleanup]  Removing old release (if exists)..."
gh release delete "$TAG" -R "$REPO" -y 2>/dev/null || true
git push origin --delete "$TAG" 2>/dev/null || true

echo ""
echo "[release] Creating new release..."

RELEASE_FILES=("$REL_BPS_MAIN" "$REL_BPS_DIGITAL" "$REL_BPS_PREVIEW")
[ -n "$REL_BPS_PRINT" ] && [ -f "$REL_BPS_PRINT" ] && RELEASE_FILES+=("$REL_BPS_PRINT")
RELEASE_FILES+=("$REL_US_EXEC" "$REL_US_PREVIEW" "$COVER_FILE")

gh release create "$TAG" \
  "${RELEASE_FILES[@]}" \
  "$CHAPTERS_DIR"/*.pdf \
  -R "$REPO" \
  --title "Beyond Popular Science / Unpopular Science — v${VERSION} (${DATESTAMP})" \
  --notes "$(cat <<NOTESEOF
v${VERSION} — built ${TIMESTAMP}

## Beyond Popular Science

| File | Description |
|------|-------------|
| \`main.pdf\` | **Digital edition** (stable URL) — 7\"×10\", centred margins, RGB, interactive, accessible |
| \`$REL_BPS_DIGITAL\` | Digital edition — symmetric margins for screen reading |
| \`$REL_BPS_PRINT\` | **Print-ready** — PDF/X-1a:2001, CMYK, US Trade 6.14\"×9.21\" |
| \`$REL_BPS_PREVIEW\` | Compressed preview |

\`\`\`bash
curl -L -o BeyondPopularScience.pdf https://github.com/$REPO/releases/download/$TAG/main.pdf
\`\`\`

## Unpopular Science (Kernel Keys Press)

| File | Description |
|------|-------------|
| \`$REL_US_EXEC\` | Executive size 7\"×10\" |
| \`$REL_US_PREVIEW\` | Compressed preview |

## Individual Chapters
52 chapter PDFs from Unpopular Science (see assets below).

## Cover
\`cover_refined.pdf\`
NOTESEOF
)"

# ---------------------------------------------------------------------------
# Cleanup temporary release copies (keep trade/executive locally)
# ---------------------------------------------------------------------------
rm -f "$REL_BPS_MAIN" "$REL_BPS_PREVIEW" "$REL_US_PREVIEW" "$REL_US_EXEC"
rm -rf "$CHAPTERS_DIR"

echo ""
echo "[ok] SUCCESS — v${VERSION} (${DATESTAMP})"
echo ""
echo "[info] Beyond Popular Science (kept locally + uploaded):"
echo "   Digital:  $REL_BPS_DIGITAL"
[ -f "$REL_BPS_PRINT" ] && \
echo "   Print:    $REL_BPS_PRINT"
echo ""
echo "[link] Stable download URL:"
echo "   curl -L -o BPS.pdf https://github.com/$REPO/releases/download/$TAG/main.pdf"
echo ""
echo "[link] Release page: https://github.com/$REPO/releases/tag/$TAG"
