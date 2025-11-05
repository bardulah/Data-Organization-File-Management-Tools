#!/bin/bash
# Example script to organize invoices by date and vendor

# This script demonstrates organizing invoice files with consistent naming
# and folder structure

INVOICE_DIR="$HOME/Documents/Invoices"
ORGANIZED_DIR="$HOME/Documents/Invoices_Organized"

echo "=== Invoice Organization Assistant ==="
echo ""

# Check if invoice directory exists
if [ ! -d "$INVOICE_DIR" ]; then
    echo "Error: Invoice directory not found: $INVOICE_DIR"
    exit 1
fi

# Step 1: Scan invoices
echo "Step 1: Scanning invoice directory..."
python3 -m fileorganizer.cli scan "$INVOICE_DIR"

echo ""
read -p "Press Enter to continue to renaming..."

# Step 2: Rename invoices with date prefix for consistent naming
# This assumes files have modification dates that reflect invoice dates
echo ""
echo "Step 2: Renaming invoices with date prefix (DRY RUN)..."
python3 -m fileorganizer.cli rename "$INVOICE_DIR" \
  --template "{date}_{name}" \
  --dry-run \
  --verbose

echo ""
read -p "Looks good? Press Enter to actually rename files..."

python3 -m fileorganizer.cli rename "$INVOICE_DIR" \
  --template "{date}_{name}" \
  --verbose

# Step 3: Organize by date (Year/Month structure)
echo ""
echo "Step 3: Organizing invoices by date (YYYY/MM structure)..."
python3 -m fileorganizer.cli organize "$INVOICE_DIR" \
  --mode date \
  --date-format "%Y/%m" \
  --target "$ORGANIZED_DIR" \
  --verbose

echo ""
echo "=== Invoice Organization Complete! ==="
echo "Organized invoices: $ORGANIZED_DIR"
echo ""
echo "Your invoices are now organized as:"
echo "  2024/"
echo "    01/  (January 2024 invoices)"
echo "    02/  (February 2024 invoices)"
echo "    ..."
