#!/bin/bash
# Example script to organize Downloads folder

# This script demonstrates how to use the File Organization Assistant
# to clean up a typical Downloads folder

DOWNLOADS_DIR="$HOME/Downloads"
ORGANIZED_DIR="$HOME/Downloads_Organized"
ARCHIVE_DIR="$HOME/Archive"

echo "=== File Organization Assistant Example ==="
echo ""

# Step 1: Scan the downloads directory
echo "Step 1: Scanning Downloads folder..."
python3 -m fileorganizer.cli scan "$DOWNLOADS_DIR" --show-duplicates

echo ""
read -p "Press Enter to continue to duplicate detection..."

# Step 2: Find and report duplicates
echo ""
echo "Step 2: Finding duplicate files..."
python3 -m fileorganizer.cli duplicates "$DOWNLOADS_DIR" \
  --action report \
  --report downloads_duplicates.txt

echo ""
read -p "Press Enter to continue to organization..."

# Step 3: Organize files by type (dry run first)
echo ""
echo "Step 3: Organizing files by type (DRY RUN)..."
python3 -m fileorganizer.cli organize "$DOWNLOADS_DIR" \
  --mode type \
  --target "$ORGANIZED_DIR" \
  --dry-run \
  --verbose

echo ""
read -p "Looks good? Press Enter to actually organize files..."

python3 -m fileorganizer.cli organize "$DOWNLOADS_DIR" \
  --mode type \
  --target "$ORGANIZED_DIR" \
  --verbose

# Step 4: Archive old files
echo ""
echo "Step 4: Archiving files older than 1 year..."
python3 -m fileorganizer.cli archive "$DOWNLOADS_DIR" \
  --mode old \
  --target "$ARCHIVE_DIR" \
  --days 365 \
  --cleanup-empty

echo ""
echo "=== Organization Complete! ==="
echo "Organized files: $ORGANIZED_DIR"
echo "Archived files: $ARCHIVE_DIR"
echo "Duplicate report: downloads_duplicates.txt"
