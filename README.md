# Challenge 1: Smooth PNG to SVG Conversion

Convert black-stroke PNG images to smooth SVG with filled paths using an enhanced Potrace pipeline.

## Overview

This project implements a custom image processing pipeline for converting line-art PNG images to smooth SVG vector graphics. The goal is "unreasonably smooth" output that preserves geometric shapes like the original artist drew them.

## Input Files

| File | Dimensions | Content |
|------|-----------|---------|
| `1.png` | 546x548 | Cartoon character (rabbit/rat) with round ears, whiskers, body outline |
| `2.png` | 528x526 | Simple stick figure/robot with round head, rectangular body, limbs |
| `3.png` | 550x544 | Additional line art |
| `4.png` | 538x540 | Additional line art |
| `5.png` | 538x552 | Additional line art |
| `6.png` | 560x576 | Additional line art |
| Background | Transparent | Black strokes on transparent |

## Output Files

| File | Dimensions | Contours | Beziers | Lines |
|------|-----------|----------|---------|-------|
| `1.svg` | 546x548 | 10 | 29 | 4 |
| `2.svg` | 528x526 | 13 | 46 | 12 |
| `3.svg` | 550x544 | 16 | 15 | 5 |
| `4.svg` | 538x540 | 16 | 16 | 6 |
| `5.svg` | 538x552 | 15 | 40 | 7 |
| `6.svg` | 560x576 | 12 | 12 | 2 |

**Note:** Current implementation uses multi-scale Bezier fitting with sliding windows for longer curves. This produces recognizable shapes but may have control point issues that cause self-intersection in some curves. The algorithm uses RDP simplification (epsilon=2.0) followed by corner detection and adaptive curve fitting.

## Pipeline Architecture

```
PNG Input
    │
    ▼
┌─────────────────────────┐
│ Phase 1: Pre-processing │
│ • Load PNG with alpha    │
│ • Bilateral filter       │  ← Edge-preserving smooth
│ • Adaptive threshold     │  ← Handle varying stroke thickness
│ • Morphological cleanup │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Phase 2: Contour        │
│   Extraction            │
│ • OpenCV findContours   │  ← Hierarchy-aware
│ • Area-based filtering  │
│ • Hierarchy analysis    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Phase 3: Curve          │
│   Smoothing             │
│ • RDP simplification    │  ← Reduce point count
│ • Corner detection      │  ← Preserve sharp corners
│ • Bezier fitting        │  ← Smooth curves
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Phase 4: SVG            │
│   Generation            │
│ • Bezier to path data   │
│ • Filled paths          │  ← Not stroked
│ • SVG structure         │
└───────────┬─────────────┘
            │
            ▼
SVG Output (1.svg, 2.svg)
```

## Key Technical Decisions

### Why Bilateral Filter?

Standard Gaussian blur smooths everything, blurring edges. Bilateral filter preserves edges while smoothing flat regions - perfect for line art.

### Why Adaptive Threshold?

Fixed threshold assumes uniform lighting. Adaptive threshold adjusts to local image characteristics, handling varying stroke thickness.

### Why RDP + Bezier?

Direct Bezier fitting on raw contours produces oscillation. RDP first simplifies to key points, then Bezier fitting produces smooth, stable curves.

### Why Corner Detection?

Without corner detection, all corners get smoothed into curves. Angle-based detection preserves intended sharp corners while smoothing gradual curves.

## Usage

```bash
# Run the conversion for all PNG files
python3 png-to-smooth-svg.py 1.png 2.png 3.png 4.png 5.png 6.png

# With custom parameters
python3 png-to-smooth-svg.py --rdp-epsilon 0.5 --corner-angle 30 1.png

# Validate results
python3 validate-results.py
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| bilateral_d | 9 | Pixel neighborhood diameter |
| bilateral_sigma_color | 75 | Color space filter strength |
| bilateral_sigma_space | 75 | Coordinate space filter strength |
| adaptive_block_size | 11 | Adaptive threshold block size |
| adaptive_c | 2 | Adaptive threshold constant |
| rdp_epsilon | 0.5 | RDP simplification tolerance (lower = more detail) |
| corner_angle | 30 | Minimum corner angle for detection (degrees) |
| line_tolerance | 2.0 | Max distance from chord to be considered straight |
| min_bezier_points | 4 | Minimum points for Bezier fitting |

## File Structure

```
challenge1/
├── 1.png                  # Input image 1
├── 2.png                  # Input image 2
├── 3.png                  # Input image 3
├── 4.png                  # Input image 4
├── 5.png                  # Input image 5
├── 6.png                  # Input image 6
├── 1.svg                  # Output SVG 1
├── 2.svg                  # Output SVG 2
├── 3.svg                  # Output SVG 3
├── 4.svg                  # Output SVG 4
├── 5.svg                  # Output SVG 5
├── 6.svg                  # Output SVG 6
├── png-to-smooth-svg.py   # Main conversion script
├── validate-results.py     # Validation script
└── README.md               # This file
```

## Testing

The validation script checks:
1. SVG syntax validity (well-formed XML)
2. File size comparison
3. Path smoothness metrics
4. Visual inspection (overlay generation)

## Dependencies

- Python 3.12+
- OpenCV 4.13+
- Pillow 12.2+
- NumPy 2.4+
- SciPy 1.17+
- Shapely 2.1+

## Results

Expected output:
- Smooth curves with no visible line segments
- Sharp corners preserved where intended
- Filled paths (not stroked lines)
- Geometric shapes match original artist intent

## Limitations

- Optimized for black strokes on transparent background
- Assumes relatively clean line art (not scanned/photographed)
- May require parameter tuning for different stroke widths
