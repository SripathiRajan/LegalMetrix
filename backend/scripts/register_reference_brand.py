#!/usr/bin/env python3
"""
CLI utility for registering authentic reference brand packaging embeddings into the LegalMetrix catalog.

Usage:
  python register_reference_brand.py --brand "Tata Salt" --image /path/to/tata_salt.png
  python register_reference_brand.py --brand "Amul Butter" --image /path/to/amul.png --logo_bbox 50 50 150 150
"""

import sys
import argparse
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.vision.authenticity import AuthenticityChecker


def parse_args():
    parser = argparse.ArgumentParser(
        description="Seed/Register verified reference brand packaging into the DINOv2 Authenticity Catalog."
    )
    parser.add_argument(
        "--brand", "-b",
        required=True,
        help="Brand identifier / name (e.g. 'Tata Salt', 'Amul Butter')"
    )
    parser.add_argument(
        "--image", "-i",
        required=True,
        help="Path to the high-resolution authentic packaging reference image"
    )
    parser.add_argument(
        "--output_dir", "-o",
        default=None,
        help="Optional custom output directory for reference embeddings (default: app/vision/reference_brands)"
    )
    parser.add_argument(
        "--logo_bbox",
        nargs=4,
        type=float,
        metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
        default=None,
        help="Optional bounding box of the brand logo [xmin ymin xmax ymax]"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    image_path = Path(args.image)

    if not image_path.exists():
        print(f"Error: Image path not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    checker = AuthenticityChecker(reference_dir=args.output_dir)
    print(f"Extracting DINOv2 visual features for brand '{args.brand}' from {image_path}...")

    saved_path = checker.save_reference_brand(
        brand_id=args.brand,
        image=image_path,
        logo_bbox=args.logo_bbox,
        brand_name=args.brand
    )

    print(f"Successfully registered reference brand '{args.brand}' -> {saved_path}")


if __name__ == "__main__":
    main()
