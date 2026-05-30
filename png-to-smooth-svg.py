#!/usr/bin/env python3
"""
png-to-smooth-svg.py

Using Potrace (via pypotrace) for bitmap tracing with true Bezier curve output.
Produces smooth, scalable SVG paths with proper corner handling.
fill-rule="evenodd" handles interior cutouts correctly.

Parameters (matching Potrace specification):
- threshold: Brightness cutoff (0-255) for binarization
- turnpolicy: How to resolve ambiguities in path decomposition
- turdsize: Suppress speckles of up to this many pixels
- corner_threshold: Smaller values = sharper corners
- opttolerance: Curve optimization tolerance
- optimize_curve: Join adjacent Bezier segments where possible
"""

import potrace
import cv2
import numpy as np
from PIL import Image
from pathlib import Path


# Potrace turn policy constants
TURNPOLICY_BLACK = potrace.POTRACE_TURNPOLICY_BLACK
TURNPOLICY_WHITE = potrace.POTRACE_TURNPOLICY_WHITE
TURNPOLICY_LEFT = potrace.POTRACE_TURNPOLICY_LEFT
TURNPOLICY_RIGHT = potrace.POTRACE_TURNPOLICY_RIGHT
TURNPOLICY_MINORITY = potrace.POTRACE_TURNPOLICY_MINORITY
TURNPOLICY_MAJORITY = potrace.POTRACE_TURNPOLICY_MAJORITY
TURNPOLICY_RANDOM = potrace.POTRACE_TURNPOLICY_RANDOM


def path_to_svg_d(path):
    """Convert a potrace Path to SVG path data string.

    Uses proper cubic Bezier curves (C command) for smooth segments
    and line segments (L command) for corners.
    """
    parts = []
    if not path or len(path) == 0:
        return ""

    # path is a list of BezierSegment or CornerSegment objects
    # Each segment has: end_point, is_corner, and for BezierSegment: c1, c2
    # For CornerSegment: c (corner point)

    # Get start point - it's the end_point of the last segment (closed path)
    if len(path) > 0:
        start_point = path[-1].end_point
        parts.append(f"M {start_point.x:.2f} {start_point.y:.2f}")

    for seg in path:
        if seg.is_corner:
            # Corner: line to corner point, then line to end point
            parts.append(f"L {seg.c.x:.2f} {seg.c.y:.2f}")
            parts.append(f"L {seg.end_point.x:.2f} {seg.end_point.y:.2f}")
        else:
            # Smooth curve: cubic Bezier with control points c1, c2 and end point
            parts.append(f"C {seg.c1.x:.2f} {seg.c1.y:.2f} {seg.c2.x:.2f} {seg.c2.y:.2f} {seg.end_point.x:.2f} {seg.end_point.y:.2f}")

    parts.append("Z")
    return " ".join(parts)


def contour_to_svg_d(contour, turdsize=2, turnpolicy=TURNPOLICY_MINORITY, alphamax=1.0,
                     opticurve=True, opttolerance=0.2, width=1000, height=1000):
    """Convert an OpenCV contour to SVG path data using Potrace.

    Creates a temporary bitmap from the contour and traces it with Potrace.
    """
    # Create a mask image from the contour
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1)

    # Also fill holes - create inverted mask for interior
    # Actually, potrace traces black on white, so we need black foreground

    # Create bitmap for potrace (needs to be inverted - potrace expects black on white)
    # blacklevel=0 means black pixels are considered "foreground"
    bmp = potrace.Bitmap(mask, blacklevel=0.5)

    # Trace with potrace
    path = bmp.trace(turdsize=turdsize, turnpolicy=turnpolicy, alphamax=alphamax,
                     opticurve=opticurve, opttolerance=opttolerance)

    return path


def png_to_svg(png_path, svg_path, threshold=128, turdsize=2, turnpolicy=TURNPOLICY_MINORITY,
               corner_threshold=1.0, opticurve=True, opttolerance=0.2,
               background_color="#ffffff", foreground_color="#000000"):
    """Convert PNG to SVG using Potrace.

    Args:
        png_path: Input PNG file path
        svg_path: Output SVG file path
        threshold: Brightness cutoff (0-255) for binarization
        turdsize: Suppress speckles of up to this many pixels
        turnpolicy: How to resolve ambiguities (TURNPOLICY_MINORITY, etc.)
        corner_threshold: Smaller values = sharper corners (alphamax in potrace)
        opticurve: Enable curve optimization
        opttolerance: Curve optimization tolerance
        background_color: Background color (#rrggbb or 'none')
        foreground_color: Foreground/stroke color
    """
    # Load image
    img = Image.open(png_path)
    w, h = img.size

    # Convert to grayscale and binarize
    if img.mode != 'L':
        img = img.convert('L')

    arr = np.array(img)

    # Binarize based on threshold
    # Invert: potrace expects black on white, but we have white strokes on black or vice versa
    # Let's detect based on threshold
    if threshold < 128:
        # Dark strokes on light background
        binary = (arr < threshold).astype(np.uint8) * 255
    else:
        # Light strokes on dark background
        binary = (arr > (threshold - 128)).astype(np.uint8) * 255

    # Trace with potrace
    bmp = potrace.Bitmap(binary, blacklevel=0.5)
    pathlist = bmp.trace(turdsize=turdsize, turnpolicy=turnpolicy,
                        alphamax=corner_threshold, opticurve=opticurve,
                        opttolerance=opttolerance)

    # Build SVG path data
    all_paths = []
    for path in pathlist:
        d = path_to_svg_d(path)
        if d:
            all_paths.append(d)

    combined = " ".join(all_paths)

    # Build SVG with parameters
    fill_attr = f' fill="{foreground_color}"'
    stroke_attr = f' stroke="{foreground_color}"' if foreground_color != 'none' else ''
    bg_fill = f' fill="{background_color}"' if background_color != 'none' else ' fill="none"'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <path d="{combined}"{fill_attr}{stroke_attr} fill-rule="evenodd"/>
</svg>'''

    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg)

    return {
        'success': True,
        'num_paths': len(all_paths),
        'width': w,
        'height': h
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert PNG to smooth SVG using Potrace')
    parser.add_argument('input', nargs='+', help='Input PNG file(s)')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--threshold', type=int, default=128,
                        help='Brightness cutoff (0-255) for binarization (default: 128)')
    parser.add_argument('--turnpolicy', default='minority',
                        choices=['black', 'white', 'left', 'right', 'minority', 'majority', 'random'],
                        help='How to resolve ambiguities (default: minority)')
    parser.add_argument('--turdsize', type=int, default=2,
                        help='Suppress speckles of up to this many pixels (default: 2)')
    parser.add_argument('--corner-threshold', type=float, default=1.0,
                        help='Corner threshold - smaller = sharper corners (default: 1.0)')
    parser.add_argument('--opttolerance', type=float, default=0.2,
                        help='Curve optimization tolerance (default: 0.2)')
    parser.add_argument('--no-opticurve', action='store_true',
                        help='Disable curve optimization')
    parser.add_argument('--background-color', default='#ffffff',
                        help='Background color (default: #ffffff)')
    parser.add_argument('--foreground-color', default='#000000',
                        help='Foreground color (default: #000000)')

    args = parser.parse_args()

    # Map turnpolicy string to constant
    turnpolicy_map = {
        'black': TURNPOLICY_BLACK,
        'white': TURNPOLICY_WHITE,
        'left': TURNPOLICY_LEFT,
        'right': TURNPOLICY_RIGHT,
        'minority': TURNPOLICY_MINORITY,
        'majority': TURNPOLICY_MAJORITY,
        'random': TURNPOLICY_RANDOM,
    }
    turnpolicy = turnpolicy_map.get(args.turnpolicy, TURNPOLICY_MINORITY)

    for input_path in args.input:
        input_file = Path(input_path)
        output_path = Path(args.output_dir) / f"{input_file.stem}.svg"

        result = png_to_svg(
            str(input_file),
            str(output_path),
            threshold=args.threshold,
            turdsize=args.turdsize,
            turnpolicy=turnpolicy,
            corner_threshold=args.corner_threshold,
            opticurve=not args.no_opticurve,
            opttolerance=args.opttolerance,
            background_color=args.background_color,
            foreground_color=args.foreground_color
        )

        print(f"{result['num_paths']} paths -> {output_path}")


if __name__ == '__main__':
    main()
