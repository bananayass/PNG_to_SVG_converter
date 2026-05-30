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

| File | Dimensions | Contours |
|------|-----------|----------|
| `1.svg` | 546x548 | 5 |
| `2.svg` | 528x526 | 7 |
| `3.svg` | 550x544 | 8 |
| `4.svg` | 538x540 | 8 |
| `5.svg` | 538x552 | 8 |
| `6.svg` | 560x576 | 6 |

**Note:** Current implementation uses Potrace (via pypotrace) for true Bezier curve tracing. Potrace produces optimal cubic Bezier curves with proper corner handling. `fill-rule="evenodd"` handles interior cutouts correctly.

## Pipeline Architecture

```
PNG Input
    │
    ▼
┌─────────────────────────┐
│ Phase 1: Pre-processing │
│ • Load PNG with PIL     │
│ • Binarize with         │  ← Threshold-based
│   threshold             │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Phase 2: Potrace        │
│   Tracing               │
│ • pypotrace.Bitmap     │  ← Creates bitmap from image
│ • bmp.trace()          │  ← Potrace algorithm
│ • Turdsize, turnpolicy │  ← Ambiguity resolution
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Phase 3: SVG            │
│   Generation            │
│ • Cubic Bezier (C)      │  ← Smooth curve segments
│ • Line (L) for corners │  ← Sharp edge preservation
│ • Fill-rule evenodd     │  ← Interior cutouts
└───────────┬─────────────┘
            │
            ▼
SVG Output (1.svg - 6.svg)
```

## Key Technical Decisions

### Why Bilateral Filter?

Standard Gaussian blur smooths everything, blurring edges. Bilateral filter preserves edges while smoothing flat regions - perfect for line art.

### Why Adaptive Threshold?

Fixed threshold assumes uniform lighting. Adaptive threshold adjusts to local image characteristics, handling varying stroke thickness.

### Why Potrace?

Potrace produces optimal cubic Bezier curves from bitmap images. It handles corner detection automatically (CornerSegment vs BezierSegment) and produces mathematically smooth curves with minimal control points.

### Why Threshold-based Binarization?

Simple thresholding works well for clean line art. The threshold parameter allows tuning for different image types (dark strokes on light bg vs light strokes on dark bg).

## Usage

```bash
# Run the conversion for all PNG files
python3 png-to-smooth-svg.py 1.png 2.png 3.png 4.png 5.png 6.png

# With custom parameters
python3 png-to-smooth-svg.py --threshold 100 --turdsize 5 --corner-threshold 0.8 1.png

# With no background
python3 png-to-smooth-svg.py --background-color none 1.png
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| threshold | 128 | Brightness cutoff (0-255) for binarization |
| turnpolicy | minority | How to resolve ambiguities in path decomposition |
| turdsize | 2 | Suppress speckles of up to this many pixels |
| corner_threshold | 1.0 | Smaller values = sharper corners (alphamax) |
| opttolerance | 0.2 | Curve optimization tolerance |
| opticurve | true | Enable curve optimization |
| foreground_color | #000000 | Foreground color after trace |
| background_color | #ffffff | Background color after trace |

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
