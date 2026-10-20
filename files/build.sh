#!/usr/bin/env bash
# Build jdc_cv.pdf: generate jdc_master.bib, then pdflatex -> biber -> pdflatex x2.
#
# Usage:  ./build.sh            (from any directory)
#         ./build.sh --no-open  (don't open the PDF afterwards)

set -e

# Always run from the directory containing this script
cd "$(dirname "$0")"

# 0. Toolchain check -------------------------------------------------------
if [ "$(uname -s)" = "Darwin" ]; then
    # Use Apple's tools and TeX Live ahead of conda/Homebrew, for this script only
    export PATH="/Library/TeX/texbin:/usr/bin:$PATH"

    # Command Line Tools provide lipo, which biber needs on Apple Silicon
    if ! xcode-select -p >/dev/null 2>&1; then
        xcode-select --install
        echo "Please finish installing the Command Line Tools, then run ./build.sh again."
        exit 1
    fi
fi

for cmd in pdflatex biber; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "MISSING: $cmd -- install MacTeX from tug.org/mactex"; exit 1; }
done

# If biber can't even start, try updating TeX Live's biber/biblatex
if ! biber --version >/dev/null 2>&1; then
    echo "biber isn't working. Trying to update it (you may be asked for your Mac password)..."
    if ! { sudo tlmgr update --self && sudo tlmgr update biber biblatex logreq; }; then
        echo "The update failed. This usually means TeX Live is an old, frozen release (e.g. 2023)."
        echo "Please install the current MacTeX from tug.org/mactex, then run ./build.sh again."
        exit 1
    fi
    if ! biber --version >/dev/null 2>&1; then
        echo "biber still won't run after updating. Please send the output of: which -a biber lipo"
        exit 1
    fi
fi


#Compile -interaction=nonstopmode keeps pdflatex from stopping to wait for
#    input on an error (the cause of builds that hang or silently do nothing).
pdflatex -interaction=nonstopmode jdc_cv >jdc_cv.pdflatex.out 2>&1 || {
    echo "pdflatex failed -- see jdc_cv.log"
    tail -n 20 jdc_cv.pdflatex.out
    exit 1
}
biber jdc_cv || { echo "biber failed -- see jdc_cv.blg"; exit 1; }
pdflatex -interaction=nonstopmode jdc_cv >/dev/null 2>&1 || true
pdflatex -interaction=nonstopmode jdc_cv >/dev/null 2>&1 || true

if grep -q '^!' jdc_cv.log; then
    echo "LaTeX errors (see jdc_cv.log):"
    grep -A2 '^!' jdc_cv.log
    exit 1
fi
echo "Built jdc_cv.pdf"

#Open the PDF
if [ "$1" != "--no-open" ]; then
    if command -v open >/dev/null 2>&1; then
        open jdc_cv.pdf            # macOS
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open jdc_cv.pdf        # Linux
    fi
fi
