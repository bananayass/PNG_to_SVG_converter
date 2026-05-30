# Challenge 1: Smooth PNG to SVG Conversion

Convert black-stroke PNG images to smooth SVG with filled paths using Potrace (potracer library).

## Overview

This project converts line-art PNG images to smooth SVG vector graphics using Potrace for bitmap tracing with true Bezier curve output. The goal is "unreasonably smooth" output that preserves geometric shapes like the original artist drew them.

## Usage

```bash
# Convert single file
python3 png-to-smooth-svg.py 1.png

# Convert multiple files
python3 png-to-smooth-svg.py 1.png 2.png 3.png

# Convert all PNGs (bash brace expansion)
python3 png-to-smooth-svg.py {1..6}.png

# With custom parameters
python3 png-to-smooth-svg.py 1.png --threshold 100 --corner-threshold 0.5

# No background rect
python3 png-to-smooth-svg.py 1.png --no-background

# Scale output
python3 png-to-smooth-svg.py 1.png --scale 2.0
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--threshold` | 128 | Brightness cutoff (0-255) for binarization |
| `--turnpolicy` | minority | How to resolve ambiguities (black/white/left/right/minority/majority) |
| `--turdsize` | 2 | Suppress speckles of up to this many pixels |
| `--corner-threshold` | 1.0 | Smaller = sharper corners (alphamax, 0-1.34) |
| `--opttolerance` | 0.2 | Curve optimization tolerance |
| `--no-opticurve` | false | Disable curve optimization |
| `--input-foreground` | Black on White | "Black on White" or "White on Black" |
| `--zero-sharp-corners` | false | Use 1.34 alphamax for sharper corners |
| `--background-color` | #ffffff | Background color |
| `--foreground-color` | #000000 | Foreground/fill color |
| `--stroke-color` | none | Stroke color |
| `--stroke-width` | 0.0 | Stroke width |
| `--scale` | 1.0 | Output scale factor |
| `--no-background` | false | No background rect |

## Input/Output Files

| Input | Output | Paths |
|-------|--------|-------|
| `1.png` (546x548) | `1.svg` | 6 |
| `2.png` (528x526) | `2.svg` | 8 |
| `3.png` (550x544) | `3.svg` | 9 |
| `4.png` (538x540) | `4.svg` | 9 |
| `5.png` (538x552) | `5.svg` | 9 |
| `6.png` (560x576) | `6.svg` | 7 |

## Dependencies

- Python 3.12+
- Pillow 12.2+
- NumPy 2.4+
- potrace (via `pip install potracer`, NOT pypotrace)

Install:
```bash
pip install potracer pillow numpy
```

**Note:** This script uses `potracer` (pure Python), not `pypotrace`. Uninstall pypotrace first if installed.

## How It Works

1. **Load image** - PIL reads PNG, extracts RGB content for grayscale conversion
2. **Binarize** - Pixels below threshold become foreground (dark strokes)
3. **Trace** - Potrace converts bitmap to polygon paths with Bezier curves
4. **Generate SVG** - Each polygon becomes a `<path>` element with fill-rule="evenodd"

## Limitations

- Optimized for black strokes on transparent/light background
- May require threshold tuning for different image types
- Input foreground detection: "Black on White" = dark strokes on light bg