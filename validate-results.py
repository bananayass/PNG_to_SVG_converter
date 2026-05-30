#!/usr/bin/env python3
"""
validate-results.py

Validates SVG output quality for PNG to SVG conversion.
"""

import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image


class ResultsValidator:
    """Validates PNG to SVG conversion results."""

    def __init__(self, input_dir='.'):
        self.input_dir = Path(input_dir)

    def validate_svg_syntax(self, svg_path):
        """Check SVG is well-formed XML."""
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            ns = '{http://www.w3.org/2000/svg}'

            if root.tag != f'{ns}svg':
                return False, f"Root tag is {root.tag}, expected {{ns}}svg"

            required_attrs = ['width', 'height', 'viewBox']
            for attr in required_attrs:
                if attr not in root.attrib:
                    return False, f"Missing required attribute: {attr}"

            # Check for paths
            paths = root.findall(f'.//{ns}path')
            if not paths:
                return False, "No path elements found"

            return True, f"Valid SVG with {len(paths)} paths"

        except ET.ParseError as e:
            return False, f"XML parse error: {e}"
        except Exception as e:
            return False, f"Error: {e}"

    def check_file_sizes(self, png_path, svg_path):
        """Compare file sizes."""
        if not os.path.exists(png_path):
            return None, f"PNG not found: {png_path}"
        if not os.path.exists(svg_path):
            return None, f"SVG not found: {svg_path}"

        png_size = os.path.getsize(png_path)
        svg_size = os.path.getsize(svg_path)

        return {
            'png_size': png_size,
            'svg_size': svg_size,
            'ratio': svg_size / png_size if png_size > 0 else 0
        }, None

    def count_svg_paths(self, svg_path):
        """Count paths and bezier curves in SVG."""
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            ns = '{http://www.w3.org/2000/svg}'

            paths = root.findall(f'.//{ns}path')
            total_commands = 0
            cubic_beziers = 0

            for path in paths:
                d = path.attrib.get('d', '')
                commands = d.split()
                total_commands += len(commands)
                cubic_beziers += d.count('C')

            return {
                'num_paths': len(paths),
                'total_commands': total_commands,
                'cubic_beziers': cubic_beziers
            }, None

        except Exception as e:
            return None, str(e)

    def check_dimensions(self, png_path, svg_path):
        """Verify SVG dimensions match PNG."""
        try:
            img = Image.open(png_path)
            png_width, png_height = img.size

            tree = ET.parse(svg_path)
            root = tree.getroot()

            svg_width = int(root.attrib.get('width', 0))
            svg_height = int(root.attrib.get('height', 0))

            match = (png_width == svg_width and png_height == svg_height)

            return {
                'png_width': png_width,
                'png_height': png_height,
                'svg_width': svg_width,
                'svg_height': svg_height,
                'match': match
            }, None

        except Exception as e:
            return None, str(e)

    def validate_conversion(self, png_name, svg_name):
        """Run all validation checks on a conversion."""
        png_path = self.input_dir / png_name
        svg_path = self.input_dir / svg_name

        results = {'png': png_name, 'svg': svg_name}

        # Syntax check
        valid, msg = self.validate_svg_syntax(svg_path)
        results['syntax_valid'] = valid
        results['syntax_message'] = msg

        # File sizes
        sizes, err = self.check_file_sizes(png_path, svg_path)
        if err:
            results['size_error'] = err
        else:
            results['png_size'] = sizes['png_size']
            results['svg_size'] = sizes['svg_size']
            results['size_ratio'] = sizes['ratio']

        # Path count
        path_info, err = self.count_svg_paths(svg_path)
        if err:
            results['path_error'] = err
        else:
            results['num_paths'] = path_info['num_paths']
            results['cubic_beziers'] = path_info['cubic_beziers']

        # Dimensions
        dims, err = self.check_dimensions(png_path, svg_path)
        if err:
            results['dim_error'] = err
        else:
            results['dimensions_match'] = dims['match']

        return results

    def print_results(self, results):
        """Print validation results."""
        print(f"\n{'='*60}")
        print(f"Validation Results: {results['png']} -> {results['svg']}")
        print('='*60)

        # Syntax
        status = "PASS" if results.get('syntax_valid') else "FAIL"
        print(f"  SVG Syntax:        [{status}] {results.get('syntax_message', 'N/A')}")

        # Dimensions
        if 'dimensions_match' in results:
            status = "PASS" if results['dimensions_match'] else "FAIL"
            print(f"  Dimensions:        [{status}] {status}")

        # File sizes
        if 'png_size' in results:
            print(f"  PNG Size:          {results['png_size']:,} bytes")
            print(f"  SVG Size:          {results['svg_size']:,} bytes")
            print(f"  Size Ratio:        {results['size_ratio']:.2f}x")

        # Paths
        if 'num_paths' in results:
            print(f"  Number of Paths:   {results['num_paths']}")
            print(f"  Cubic Beziers:     {results['cubic_beziers']}")

        # Overall
        all_pass = (
            results.get('syntax_valid', False) and
            results.get('dimensions_match', False)
        )
        overall = "PASS" if all_pass else "FAIL"
        print(f"\n  OVERALL:           [{overall}]")

        return all_pass

    def validate_all(self):
        """Validate all conversions in directory."""
        # Expected conversions
        conversions = [
            ('1.png', '1.svg'),
            ('2.png', '2.svg'),
        ]

        all_pass = True
        for png_name, svg_name in conversions:
            results = self.validate_conversion(png_name, svg_name)
            passed = self.print_results(results)
            if not passed:
                all_pass = False

        print(f"\n{'='*60}")
        if all_pass:
            print("ALL VALIDATIONS PASSED")
        else:
            print("SOME VALIDATIONS FAILED")
        print('='*60)

        return 0 if all_pass else 1


def main():
    """Run validation."""
    import argparse

    parser = argparse.ArgumentParser(description='Validate SVG conversion results')
    parser.add_argument('--dir', default='.', help='Directory containing files')

    args = parser.parse_args()

    validator = ResultsValidator(args.dir)
    return validator.validate_all()


if __name__ == '__main__':
    sys.exit(main())
