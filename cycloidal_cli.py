"""Standalone CLI and profile exporter for Cycloidal Drive Generator.

Supports exporting profiles and drive geometry to SVG, DXF (R12 ASCII),
CSV, and JSON formats without external third-party dependencies.
"""

import argparse
import json
import math
import sys
from typing import List, Tuple

import cycloidal_core
from cycloidal_core import CycloidalDriveConfig


def export_svg(config: CycloidalDriveConfig, filepath: str, stroke_width: float = 0.05) -> None:
    """Export the cycloidal rotor, pins, center bore, and drive holes as an SVG file."""
    points = cycloidal_core.generate_full_rotor_profile(config)
    pin_centers = cycloidal_core.generate_pin_centers(config)
    hole_centers = cycloidal_core.generate_drive_hole_centers(config)

    # Calculate bounding box with margin
    max_dim = config.R + config.roller_radius + 0.5
    vb_min = -max_dim
    vb_size = 2.0 * max_dim

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_min:.4f} {vb_min:.4f} {vb_size:.4f} {vb_size:.4f}" width="800" height="800">',
        '  <style>',
        '    .housing-circle { stroke: #aaa; stroke-dasharray: 0.2, 0.2; fill: none; }',
        '    .pin { stroke: #d9534f; fill: #fdf7f7; fill-opacity: 0.6; }',
        '    .rotor { stroke: #0275d8; fill: #eef7fd; fill-opacity: 0.7; stroke-linejoin: round; }',
        '    .bore { stroke: #333; fill: #ffffff; }',
        '    .drive-hole { stroke: #5cb85c; fill: #ffffff; }',
        '  </style>',
        f'  <!-- Housing Pin Pitch Circle R={config.R} -->',
        f'  <circle class="housing-circle" cx="0" cy="0" r="{config.R:.4f}" stroke-width="{stroke_width}"/>',
    ]

    # Pins
    for px, py in pin_centers:
        svg_lines.append(
            f'  <circle class="pin" cx="{px:.4f}" cy="{py:.4f}" r="{config.roller_radius:.4f}" stroke-width="{stroke_width}"/>'
        )

    # Rotor Profile (eccentrically placed or origin-centered; export origin-centered)
    path_data = [f"M {points[0][0]:.4f} {points[0][1]:.4f}"]
    for x, y in points[1:]:
        path_data.append(f"L {x:.4f} {y:.4f}")
    path_data.append("Z")

    svg_lines.append(f'  <path class="rotor" d="{" ".join(path_data)}" stroke-width="{stroke_width}"/>')

    # Central bore
    if config.bore_diameter > 0:
        bore_r = config.bore_diameter / 2.0
        svg_lines.append(
            f'  <circle class="bore" cx="0" cy="0" r="{bore_r:.4f}" stroke-width="{stroke_width}"/>'
        )

    # Drive pin holes
    if config.num_holes > 0 and config.hole_pin_diameter > 0:
        hole_r = (config.hole_pin_diameter / 2.0) + config.eccentricity
        for hx, hy in hole_centers:
            svg_lines.append(
                f'  <circle class="drive-hole" cx="{hx:.4f}" cy="{hy:.4f}" r="{hole_r:.4f}" stroke-width="{stroke_width}"/>'
            )

    svg_lines.append('</svg>\n')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg_lines))


def export_dxf(config: CycloidalDriveConfig, filepath: str) -> None:
    """Export the rotor profile as an AutoCAD DXF R12 standard polyline file."""
    points = cycloidal_core.generate_full_rotor_profile(config)

    # Native standard DXF R12 output
    lines = [
        "0", "SECTION",
        "2", "ENTITIES",
        "0", "POLYLINE",
        "8", "ROTOR",
        "66", "1",
        "70", "1",  # 1 = closed polyline
        "10", "0.0",
        "20", "0.0",
        "30", "0.0",
    ]

    for x, y in points[:-1]:  # closed polyline flag 70 handles connecting last to first
        lines.extend([
            "0", "VERTEX",
            "8", "ROTOR",
            "10", f"{x:.6f}",
            "20", f"{y:.6f}",
            "30", "0.0",
        ])

    lines.extend([
        "0", "SEQEND",
        "0", "ENDSEC",
        "0", "EOF",
        "",
    ])

    with open(filepath, "w", encoding="ascii") as f:
        f.write("\n".join(lines))


def export_csv(config: CycloidalDriveConfig, filepath: str) -> None:
    """Export profile points to CSV."""
    points = cycloidal_core.generate_full_rotor_profile(config)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("index,x,y\n")
        for i, (x, y) in enumerate(points):
            f.write(f"{i},{x:.6f},{y:.6f}\n")


def export_json(config: CycloidalDriveConfig, filepath: str) -> None:
    """Export drive parameters and generated profile coordinates to JSON."""
    rotor_points = cycloidal_core.generate_full_rotor_profile(config)
    pin_centers = cycloidal_core.generate_pin_centers(config)
    hole_centers = cycloidal_core.generate_drive_hole_centers(config)

    data = {
        "parameters": {
            "R": config.R,
            "N": config.N,
            "reduction_ratio": config.reduction_ratio,
            "roller_radius": config.roller_radius,
            "eccentricity": config.eccentricity,
            "eccentricity_ratio": config.eccentricity_ratio,
            "rotor_thickness": config.rotor_thickness,
            "housing_thickness": config.housing_thickness,
            "bore_diameter": config.bore_diameter,
            "num_holes": config.num_holes,
            "hole_pin_diameter": config.hole_pin_diameter,
            "hole_circle_diameter": config.hole_circle_diameter,
            "num_gears": config.num_gears,
        },
        "rotor_profile_points": [{"x": x, "y": y} for x, y in rotor_points],
        "pins": [
            {"x": px, "y": py, "radius": config.roller_radius}
            for px, py in pin_centers
        ],
        "drive_holes": [
            {
                "x": hx,
                "y": hy,
                "radius": (config.hole_pin_diameter / 2.0) + config.eccentricity,
            }
            for hx, hy in hole_centers
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cycloidal Reduction Drive Generator & Profile Exporter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-R", "--radius", type=float, default=5.0, help="Pitch radius of pin housing")
    parser.add_argument("-N", "--num-pins", type=int, default=10, help="Number of housing pins (ratio is N - 1)")
    parser.add_argument("-e", "--eccentricity-ratio", type=float, default=0.5, help="Eccentricity ratio relative to pin radius")
    parser.add_argument("-t", "--rotor-thickness", type=float, default=0.635, help="Rotor thickness")
    parser.add_argument("-b", "--bore", type=float, default=1.0, help="Central bore diameter")
    parser.add_argument("--num-holes", type=int, default=0, help="Number of output drive holes")
    parser.add_argument("--pin-diameter", type=float, default=0.25, help="Output pin diameter")
    parser.add_argument("--hole-circle-diameter", type=float, default=3.0, help="Drive hole circle diameter")
    parser.add_argument("--num-gears", type=int, default=1, help="Number of stacked rotor discs")
    parser.add_argument("--export-svg", type=str, help="Export 2D preview / cut file to SVG")
    parser.add_argument("--export-dxf", type=str, help="Export 2D rotor profile to AutoCAD R12 DXF")
    parser.add_argument("--export-csv", type=str, help="Export full profile coordinates to CSV")
    parser.add_argument("--export-json", type=str, help="Export configuration and points to JSON")
    parser.add_argument("--validate-only", action="store_true", help="Only validate parameters and print specs")
    return parser


def main(argv: List[str] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = CycloidalDriveConfig(
        R=args.radius,
        N=args.num_pins,
        eccentricity_ratio=args.eccentricity_ratio,
        rotor_thickness=args.rotor_thickness,
        bore_diameter=args.bore,
        num_holes=args.num_holes,
        hole_pin_diameter=args.pin_diameter,
        hole_circle_diameter=args.hole_circle_diameter,
        num_gears=args.num_gears,
    )

    errors = config.validate()
    if errors:
        print("Configuration validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("Cycloidal Gear Parameters:")
    print(f"  Pitch radius R: {config.R}")
    print(f"  Housing pins N: {config.N}")
    print(f"  Rotor lobes: {config.num_lobes}")
    print(f"  Reduction ratio: {config.reduction_ratio}:1")
    print(f"  Roller radius Rr: {config.roller_radius:.4f}")
    print(f"  Eccentricity E: {config.eccentricity:.4f}")

    if args.validate_only:
        return 0

    if args.export_svg:
        export_svg(config, args.export_svg)
        print(f"Exported SVG to {args.export_svg}")

    if args.export_dxf:
        export_dxf(config, args.export_dxf)
        print(f"Exported DXF to {args.export_dxf}")

    if args.export_csv:
        export_csv(config, args.export_csv)
        print(f"Exported CSV to {args.export_csv}")

    if args.export_json:
        export_json(config, args.export_json)
        print(f"Exported JSON to {args.export_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
