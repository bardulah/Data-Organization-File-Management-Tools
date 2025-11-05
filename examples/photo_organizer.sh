#!/bin/bash
# Example script to organize photo library

# This script demonstrates organizing photos by date and finding duplicates

PHOTO_DIR="$HOME/Pictures/Photos"
ORGANIZED_DIR="$HOME/Pictures/Photos_Organized"
DUPLICATES_DIR="$HOME/Pictures/Photo_Duplicates"

echo "=== Photo Library Organization Assistant ==="
echo ""

# Check if photo directory exists
if [ ! -d "$PHOTO_DIR" ]; then
    echo "Error: Photo directory not found: $PHOTO_DIR"
    exit 1
fi

# Step 1: Scan and analyze photos
echo "Step 1: Scanning photo library..."
python3 -m fileorganizer.cli scan "$PHOTO_DIR" \
  --show-duplicates \
  --output photo_scan_results.json

echo ""
read -p "Press Enter to continue to duplicate detection..."

# Step 2: Find and move duplicate photos
echo ""
echo "Step 2: Finding duplicate photos..."
python3 -m fileorganizer.cli duplicates "$PHOTO_DIR" \
  --action move \
  --target "$DUPLICATES_DIR" \
  --keep newest \
  --dry-run \
  --verbose

echo ""
read -p "Ready to move duplicates? Press Enter..."

python3 -m fileorganizer.cli duplicates "$PHOTO_DIR" \
  --action move \
  --target "$DUPLICATES_DIR" \
  --keep newest \
  --verbose

# Step 3: Organize photos by date (Year/Month/Day)
echo ""
echo "Step 3: Organizing photos by date (YYYY/MM/DD structure)..."
python3 -m fileorganizer.cli organize "$PHOTO_DIR" \
  --mode date \
  --date-format "%Y/%m/%d" \
  --target "$ORGANIZED_DIR" \
  --verbose

# Step 4: Rename photos with consistent naming
echo ""
echo "Step 4: Renaming photos with date and counter..."
python3 -m fileorganizer.cli rename "$ORGANIZED_DIR" \
  --template "{date}_{counter}" \
  --dry-run \
  --verbose

echo ""
read -p "Apply renaming? Press Enter or Ctrl+C to skip..."

python3 -m fileorganizer.cli rename "$ORGANIZED_DIR" \
  --template "{date}_{counter}" \
  --verbose

echo ""
echo "=== Photo Organization Complete! ==="
echo "Organized photos: $ORGANIZED_DIR"
echo "Duplicate photos: $DUPLICATES_DIR"
echo "Scan results: photo_scan_results.json"
