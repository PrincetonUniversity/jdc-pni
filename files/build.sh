#!/usr/bin/env bash
# Build jdc_cv.pdf: generate jdc_master.bib, then pdflatex -> biber -> pdflatex x2.
#
# Usage:  ./build.sh            (from any directory)
#         ./build.sh --no-open  (don't open the PDF afterwards)

set -e

# Always run from the directory containing this script
cd "$(dirname "$0")"

# 1. Generate the master bibliography (any Python 3.6+ works; no packages needed)
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
else
    PYTHON=python
fi
"$PYTHON" make_master_bib.py

# 2. Compile. -interaction=nonstopmode keeps pdflatex from stopping to wait for
#    input on an error (the cause of builds that hang or silently do nothing).
pdflatex -interaction=nonstopmode jdc_cv >/dev/null || true
biber jdc_cv || { echo "biber failed -- see jdc_cv.blg"; exit 1; }
pdflatex -interaction=nonstopmode jdc_cv >/dev/null || true
pdflatex -interaction=nonstopmode jdc_cv >/dev/null || true

if grep -q '^!' jdc_cv.log; then
    echo "LaTeX errors (see jdc_cv.log):"
    grep -A2 '^!' jdc_cv.log
    exit 1
fi
echo "Built jdc_cv.pdf"

# 3. Open the PDF
if [ "$1" != "--no-open" ]; then
    if command -v open >/dev/null 2>&1; then
        open jdc_cv.pdf            # macOS
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open jdc_cv.pdf        # Linux
    fi
fi
