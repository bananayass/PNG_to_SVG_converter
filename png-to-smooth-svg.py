#!/usr/bin/env python3
"""
png-to-smooth-svg.py

Using Catmull-Rom spline smoothing with corner detection.
Corner-aware smoothing preserves sharp turns while smoothing curves.
fill-rule="evenodd" handles interior cutouts correctly.
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path


def angle_at(pts, i):
    """Measure turn angle at point i (interior angle of turn)."""
    n = len(pts)
    v1 = pts[i] - pts[(i - 1) % n]
    v2 = pts[(i + 1) % n] - pts[i]
    l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if l1 < 1e-10 or l2 < 1e-10:
        return 0.0
    cos_a = np.clip(np.dot(v1, v2) / (l1 * l2), -1, 1)
    return np.degrees(np.arccos(cos_a))


def contour_to_path(cnt, simp_epsilon=1.5, smooth_tension=0.25, corner_thresh=25):
    """Convert a contour to SVG path using Catmull-Rom with corner preservation."""
    approx = cv2.approxPolyDP(cnt, simp_epsilon, closed=True)
    pts = approx.reshape(-1, 2).astype(float)
    n = len(pts)
    if n < 2:
        return ""

    # Detect sharp corners (high angle change = corner)
    is_corner = []
    for i in range(n):
        a = angle_at(pts, i)
        is_corner.append(a > corner_thresh)

    parts = [f"M {pts[0][0]:.2f} {pts[0][1]:.2f}"]

    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]

        # If either endpoint is a corner, use a line segment
        if is_corner[i] or is_corner[(i + 1) % n]:
            parts.append(f"L {p2[0]:.2f} {p2[1]:.2f}")
        else:
            # Smooth with Catmull-Rom spline
            p0 = pts[(i - 1) % n]
            p3 = pts[(i + 2) % n]

            cp1 = p1 + smooth_tension * (p2 - p0)
            cp2 = p2 - smooth_tension * (p3 - p1)
            parts.append(f"C {cp1[0]:.2f} {cp1[1]:.2f} {cp2[0]:.2f} {cp2[1]:.2f} {p2[0]:.2f} {p2[1]:.2f}")

    parts.append("Z")
    return " ".join(parts)


def png_to_svg(png_path, svg_path, simp_epsilon=1.5, smooth_tension=0.25, corner_thresh=25):
    """Convert PNG to SVG with Catmull-Rom smoothing and corner preservation."""
    # Load image
    img = Image.open(png_path)
    w, h = img.size

    # Extract black strokes
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    arr = np.array(img)
    mask = ((arr[:, :, 0] < 30) &
            (arr[:, :, 1] < 30) &
            (arr[:, :, 2] < 30) &
            (arr[:, :, 3] > 128)).astype(np.uint8) * 255

    # Find contours
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Build paths for all contours
    all_ds = []
    for cnt in contours:
        if cv2.contourArea(cnt) < 30:
            continue
        d = contour_to_path(cnt, simp_epsilon=simp_epsilon, smooth_tension=smooth_tension, corner_thresh=corner_thresh)
        if d:
            all_ds.append(d)

    # Combine into single path with evenodd fill
    combined = " ".join(all_ds)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <path d="{combined}" fill="black" fill-rule="evenodd" stroke="none"/>
</svg>'''

    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg)

    return {
        'success': True,
        'num_contours': len(all_ds),
        'width': w,
        'height': h
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert PNG to smooth SVG')
    parser.add_argument('input', nargs='+', help='Input PNG file(s)')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    parser.add_argument('--simp-epsilon', type=float, default=1.5,
                        help='Simplification epsilon (default: 1.5)')
    parser.add_argument('--smooth-tension', type=float, default=0.25,
                        help='Catmull-Rom tension (default: 0.25)')
    parser.add_argument('--corner-thresh', type=float, default=25,
                        help='Corner angle threshold in degrees (default: 25)')

    args = parser.parse_args()

    for input_path in args.input:
        input_file = Path(input_path)
        output_path = Path(args.output_dir) / f"{input_file.stem}.svg"

        result = png_to_svg(
            str(input_file),
            str(output_path),
            simp_epsilon=args.simp_epsilon,
            smooth_tension=args.smooth_tension,
            corner_thresh=args.corner_thresh
        )

        print(f"{result['num_contours']} contours -> {output_path}")


if __name__ == '__main__':
    main()