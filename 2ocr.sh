#!/bin/bash

# Directory containing TIFF files
INPUT_DIR="atreatiseonlawp00chitgoog_tif"
OUTPUT_PDF="output_searchable.pdf"
TEMP_DIR="temp_ocr"

# Create a temporary directory to store processed files
mkdir -p "$TEMP_DIR"

# Process each TIFF file
for file in "$INPUT_DIR"/*.tif; do
  # Extract the filename without extension
  filename=$(basename "$file" .tif)

  # Run Tesseract on each file and output a PDF for each page
  tesseract "$file" "$TEMP_DIR/$filename" -l eng pdf
done

# Combine all individual page PDFs into a single PDF
if command -v pdfunite >/dev/null 2>&1; then
  # If pdfunite is available (from poppler-utils), use it
  pdfunite "$TEMP_DIR"/*.pdf "$OUTPUT_PDF"
else
  # Fallback to using ImageMagick's `convert` if `pdfunite` isn't available
  convert "$TEMP_DIR"/*.pdf "$OUTPUT_PDF"
fi

# Clean up temporary directory
rm -r "$TEMP_DIR"

echo "Searchable PDF created as $OUTPUT_PDF"