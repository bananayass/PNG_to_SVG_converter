#!/usr/bin/env python3
"""
png-to-smooth-svg.py

Converts PNG to smooth SVG using Potrace with true Bezier curve output.
Based on the ComfyUI-ToSVG-Potracer implementation.

Parameters:
- threshold: Brightness cutoff (0-255) for binarization
- turnpolicy: How to resolve ambiguities in path decomposition
- turdsize: Suppress speckles of up to this many pixels
- corner_threshold: Smaller values = sharper corners (alphamax)
- opttolerance: Curve optimization tolerance
- optimize_curve: Join adjacent Bezier segments where possible
"""

import potrace
import numpy as np
from PIL import Image
from pathlib import Path
import argparse


# Potrace turn policy constants
TURNPOLICY_BLACK = potrace.POTRACE_TURNPOLICY_BLACK
TURNPOLICY_WHITE = potrace.POTRACE_TURNPOLICY_WHITE
TURNPOLICY_LEFT = potrace.POTRACE_TURNPOLICY_LEFT
TURNPOLICY_RIGHT = potrace.POTRACE_TURNPOLICY_RIGHT
TURNPOLICY_MINORITY = potrace.POTRACE_TURNPOLICY_MINORITY
TURNPOLICY_MAJORITY = potrace.POTRACE_TURNPOLICY_MAJORITY


def path_to_svg_d(path, scale=1.0):
    """Convert a potrace Path (polygon) to SVG path data string.

    Uses proper cubic Bezier curves (C command) for smooth segments
    and line segments (L command) for corners.
    """
    parts = []
    if not path:
        return ""

    # Get start point from the path's start_point attribute
    start = path.start_point
    parts.append(f"M{start.x * scale:.2f},{start.y * scale:.2f}")

    # Iterate through segments
    for segment in path.segments:
        if segment.is_corner:
            # Corner: line to corner point (c), then line to end point
            c_x = segment.c.x * scale
            c_y = segment.c.y * scale
            ep_x = segment.end_point.x * scale
            ep_y = segment.end_point.y * scale
            parts.append(f"L{c_x:.2f},{c_y:.2f}L{ep_x:.2f},{ep_y:.2f}")
        else:
            # Smooth curve: cubic Bezier with control points c1, c2 and end point
            c1_x = segment.c1.x * scale
            c1_y = segment.c1.y * scale
            c2_x = segment.c2.x * scale
            c2_y = segment.c2.y * scale
            ep_x = segment.end_point.x * scale
            ep_y = segment.end_point.y * scale
            parts.append(f"C{c1_x:.2f},{c1_y:.2f} {c2_x:.2f},{c2_y:.2f} {ep_x:.2f},{ep_y:.2f}")

    parts.append("Z")
    return "".join(parts)


def png_to_svg(png_path, svg_path, threshold=128, turdsize=2, turnpolicy=TURNPOLICY_MINORITY,
               corner_threshold=1.0, opticurve=True, opttolerance=0.2,
               background_color="#ffffff", foreground_color="#000000",
               stroke_color="none", stroke_width=0.0,
               input_foreground="Black on White", zero_sharp_corners=False,
               output_scale=1.0, no_background=False):
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
        stroke_color: Stroke color
        stroke_width: Stroke width
        input_foreground: "Black on White" or "White on Black"
        zero_sharp_corners: If True, use alphamax=1.34 for sharper corners
        output_scale: Output scale factor
        no_background: If True, no background rect
    """
    # Load image
    img = Image.open(png_path)
    orig_width, orig_height = img.size

    # Convert to numpy array and binarize
    if img.mode == 'RGBA':
        # Use RGB content for threshold detection, alpha as mask
        rgb_arr = np.array(img)[:, :, :3]
        alpha_arr = np.array(img)[:, :, 3]
        # Compute grayscale from RGB
        arr = (0.299 * rgb_arr[:,:,0] + 0.587 * rgb_arr[:,:,1] + 0.114 * rgb_arr[:,:,2]).astype(np.uint8)
    elif img.mode == 'RGB':
        rgb_arr = np.array(img)
        arr = (0.299 * rgb_arr[:,:,0] + 0.587 * rgb_arr[:,:,1] + 0.114 * rgb_arr[:,:,2]).astype(np.uint8)
    elif img.mode == 'L':
        arr = np.array(img)
    else:
        img = img.convert('L')
        arr = np.array(img)

    # Calculate scaled dimensions
    scale = max(0.01, output_scale)
    scaled_width = max(1, round(orig_width * scale))
    scaled_height = max(1, round(orig_height * scale))

    # Normalize threshold to 0-1 range for comparison
    threshold_norm = threshold / 255.0

    # Binarize the image
    if arr.ndim == 3:
        # Take first channel if multi-channel
        binary_np = arr[:, :, 0] < threshold_norm
    else:
        binary_np = arr < threshold_norm

    # For "Black on White" input: dark strokes on light background
    # Pixels below threshold (dark) become True (foreground) - no invert needed
    # For "White on Black" input: light strokes on dark background
    # We need to invert so light strokes become True (foreground)
    if input_foreground == "White on Black":
        binary_np = ~binary_np

    # Check for blank images
    if np.all(binary_np) or not np.any(binary_np):
        svg = f'''<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="{scaled_width}" height="{scaled_height}" viewBox="0 0 {scaled_width} {scaled_height}">
  <rect width="100%" height="100%" fill="{background_color}"/>
</svg>'''
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg)
        return {'success': True, 'num_paths': 0, 'width': scaled_width, 'height': scaled_height}

    # Determine alphamax (corner threshold)
    alphamax = 1.34 if zero_sharp_corners else corner_threshold

    # Create bitmap and trace
    bm = potrace.Bitmap(binary_np)
    plist = bm.trace(
        turdsize=turdsize,
        turnpolicy=turnpolicy,
        alphamax=alphamax,
        opticurve=opticurve,
        opttolerance=opttolerance
    )

    # Build SVG
    svg_header = f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{scaled_width}" height="{scaled_height}" viewBox="0 0 {scaled_width} {scaled_height}">'
    svg_footer = "</svg>"

    # Background rect
    background_rect = ""
    bg_color_lower = background_color.lower()
    if not no_background and bg_color_lower != "none" and bg_color_lower != "":
        background_rect = f'<rect width="100%" height="100%" fill="{background_color}"/>'

    # Stroke and fill attributes
    scaled_stroke_width = stroke_width * scale
    if scaled_stroke_width > 0 and stroke_color.lower() != "none":
        stroke_attr = f'stroke="{stroke_color}" stroke-width="{scaled_stroke_width}"'
    else:
        stroke_attr = 'stroke="none"'

    if foreground_color.lower() != "none":
        fill_attr = f'fill="{foreground_color}"'
    else:
        fill_attr = 'fill="none"'

    # Fallback if neither fill nor stroke
    if fill_attr == 'fill="none"' and stroke_attr == 'stroke="none"':
        fill_attr = 'fill="black"'

    # Build path data
    all_paths_parts = []
    if plist:
        fill_rule = "evenodd"
        for curve in plist:
            if not (hasattr(curve, 'start_point') and hasattr(curve.start_point, 'x') and hasattr(curve.start_point, 'y')):
                continue

            fs = curve.start_point
            all_paths_parts.append(f"M{fs.x * scale:.2f},{fs.y * scale:.2f}")

            if not hasattr(curve, 'segments'):
                continue

            for segment in curve.segments:
                valid = (hasattr(segment, 'is_corner') and
                         hasattr(segment, 'end_point') and
                         hasattr(segment.end_point, 'x') and
                         hasattr(segment.end_point, 'y'))

                if valid and segment.is_corner:
                    if hasattr(segment, 'c') and hasattr(segment.c, 'x') and hasattr(segment.c, 'y'):
                        c_x = segment.c.x * scale
                        c_y = segment.c.y * scale
                        ep_x = segment.end_point.x * scale
                        ep_y = segment.end_point.y * scale
                        all_paths_parts.append(f"L{c_x:.2f},{c_y:.2f}L{ep_x:.2f},{ep_y:.2f}")
                elif valid:
                    if (hasattr(segment, 'c1') and hasattr(segment.c1, 'x') and hasattr(segment.c1, 'y') and
                        hasattr(segment, 'c2') and hasattr(segment.c2, 'x') and hasattr(segment.c2, 'y')):
                        c1_x = segment.c1.x * scale
                        c1_y = segment.c1.y * scale
                        c2_x = segment.c2.x * scale
                        c2_y = segment.c2.y * scale
                        ep_x = segment.end_point.x * scale
                        ep_y = segment.end_point.y * scale
                        all_paths_parts.append(f"C{c1_x:.2f},{c1_y:.2f} {c2_x:.2f},{c2_y:.2f} {ep_x:.2f},{ep_y:.2f}")

            all_paths_parts.append("Z")

    if all_paths_parts:
        path_d = "".join(all_paths_parts)
        path_element = f'<path {stroke_attr} {fill_attr} fill-rule="{fill_rule}" d="{path_d}"/>'
        svg_content = svg_header + background_rect + path_element + svg_footer
    else:
        svg_content = f'{svg_header}<desc>No paths found</desc>{svg_footer}'

    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    return {
        'success': True,
        'num_paths': len(plist) if plist else 0,
        'width': scaled_width,
        'height': scaled_height
    }


def main():
    parser = argparse.ArgumentParser(description='Convert PNG to smooth SVG using Potrace')
    parser.add_argument('input', nargs='+', help='Input PNG file(s)')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--threshold', type=int, default=128,
                        help='Brightness cutoff (0-255) for binarization (default: 128)')
    parser.add_argument('--turnpolicy', default='minority',
                        choices=['black', 'white', 'left', 'right', 'minority', 'majority'],
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
    parser.add_argument('--stroke-color', default='none',
                        help='Stroke color (default: none)')
    parser.add_argument('--stroke-width', type=float, default=0.0,
                        help='Stroke width (default: 0.0)')
    parser.add_argument('--input-foreground', default='Black on White',
                        choices=['Black on White', 'White on Black'],
                        help='Foreground/background orientation (default: Black on White)')
    parser.add_argument('--zero-sharp-corners', action='store_true',
                        help='Use 1.34 alphamax for sharper corners')
    parser.add_argument('--scale', type=float, default=1.0,
                        help='Output scale factor (default: 1.0)')
    parser.add_argument('--no-background', action='store_true',
                        help='No background rect')

    args = parser.parse_args()

    # Map turnpolicy string to constant
    turnpolicy_map = {
        'black': TURNPOLICY_BLACK,
        'white': TURNPOLICY_WHITE,
        'left': TURNPOLICY_LEFT,
        'right': TURNPOLICY_RIGHT,
        'minority': TURNPOLICY_MINORITY,
        'majority': TURNPOLICY_MAJORITY,
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
            foreground_color=args.foreground_color,
            stroke_color=args.stroke_color,
            stroke_width=args.stroke_width,
            input_foreground=args.input_foreground,
            zero_sharp_corners=args.zero_sharp_corners,
            output_scale=args.scale,
            no_background=args.no_background
        )

        print(f"{result['num_paths']} paths -> {output_path}")


if __name__ == '__main__':
    main()