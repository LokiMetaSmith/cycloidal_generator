"""Unit and regression tests for cycloidal drive generator."""

import json
import math
import os
import subprocess
import tempfile
import pytest

import cycloidal_core
from cycloidal_core import CycloidalDriveConfig
import cycloidal_cli


class TestCycloidalMath:
    """Test pure mathematical formulas and periodicity of cycloidal tooth generation."""

    def test_get_point_initial_and_periodic(self):
        R = 5.0
        N = 10
        Rr = (2.0 * R * math.pi) / (4.0 * N)
        E = 0.5 * Rr

        x0, y0 = cycloidal_core.get_point(0.0, R, Rr, E, N)
        assert isinstance(x0, float)
        assert isinstance(y0, float)

        # Periodicity: after 2*pi, point should match t=0
        x2pi, y2pi = cycloidal_core.get_point(2.0 * math.pi, R, Rr, E, N)
        assert math.isclose(x0, x2pi, abs_tol=1e-7)
        assert math.isclose(y0, y2pi, abs_tol=1e-7)

    def test_get_distance(self):
        assert cycloidal_core.get_distance(0, 0, 3, 4) == 5.0
        assert cycloidal_core.get_distance(1, 1, 1, 1) == 0.0


class TestCycloidalConfigAndValidation:
    """Test configuration validation and edge cases."""

    def test_valid_default_configuration(self):
        cfg = CycloidalDriveConfig(R=5.0, N=10, bore_diameter=1.0)
        errors = cfg.validate()
        assert errors == []
        assert cfg.num_lobes == 9
        assert cfg.reduction_ratio == 9
        assert cfg.roller_radius > 0
        assert cfg.eccentricity > 0

    def test_invalid_negative_dimensions(self):
        cfg = CycloidalDriveConfig(R=-5.0, N=10)
        errors = cfg.validate()
        assert any("Housing pitch radius R must be positive" in e for e in errors)

        cfg_n = CycloidalDriveConfig(R=5.0, N=1)
        errors_n = cfg_n.validate()
        assert any("Number of pins N must be at least 2" in e for e in errors_n)

    def test_undercut_and_self_intersection_detection(self):
        # Very high eccentricity ratio causing E * N >= R
        cfg = CycloidalDriveConfig(R=2.0, N=10, eccentricity_ratio=5.0)
        errors = cfg.validate()
        assert any("causing self-intersection" in e for e in errors)

    def test_bore_and_drive_hole_boundary_collision(self):
        # Bore larger than rotor root
        cfg_bore = CycloidalDriveConfig(R=5.0, N=10, bore_diameter=15.0)
        errors = cfg_bore.validate()
        assert any("exceeds approx rotor root radius" in e for e in errors)

        # Drive holes colliding with bore
        cfg_holes = CycloidalDriveConfig(
            R=5.0,
            N=10,
            bore_diameter=3.0,
            num_holes=4,
            hole_pin_diameter=1.0,
            hole_circle_diameter=3.2,
        )
        errors = cfg_holes.validate()
        assert any("collide with central bore" in e for e in errors)


class TestProfileGeneration:
    """Test point generation for single lobe and full closed profile."""

    def test_single_lobe_points_continuity(self):
        cfg = CycloidalDriveConfig(R=5.0, N=10)
        pts = cycloidal_core.generate_single_lobe_points(cfg)
        assert len(pts) > 10

        # Verify distance between consecutive points satisfies constraints
        for i in range(len(pts) - 1):
            d = cycloidal_core.get_distance(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
            assert d <= cfg.max_point_dist * 1.05

    def test_full_rotor_profile_closed(self):
        cfg = CycloidalDriveConfig(R=5.0, N=10)
        pts = cycloidal_core.generate_full_rotor_profile(cfg, num_samples_per_lobe=20)
        assert len(pts) == (cfg.N - 1) * 20 + 1
        # Start and end points must be equal
        assert pts[0] == pts[-1]

    def test_pin_and_hole_centers(self):
        cfg = CycloidalDriveConfig(
            R=5.0, N=8, num_holes=4, hole_circle_diameter=3.0, hole_pin_diameter=0.5
        )
        pins = cycloidal_core.generate_pin_centers(cfg)
        assert len(pins) == 8
        for px, py in pins:
            assert math.isclose(math.hypot(px, py), 5.0, rel_tol=1e-6)

        holes = cycloidal_core.generate_drive_hole_centers(cfg)
        assert len(holes) == 4
        for hx, hy in holes:
            assert math.isclose(math.hypot(hx, hy), 1.5, rel_tol=1e-6)


class TestExportersAndCLI:
    """Test exporters and CLI execution."""

    def test_exports_produce_valid_files(self):
        cfg = CycloidalDriveConfig(
            R=5.0,
            N=8,
            bore_diameter=1.0,
            num_holes=4,
            hole_pin_diameter=0.4,
            hole_circle_diameter=2.5,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = os.path.join(tmpdir, "test.svg")
            dxf_path = os.path.join(tmpdir, "test.dxf")
            csv_path = os.path.join(tmpdir, "test.csv")
            json_path = os.path.join(tmpdir, "test.json")

            cycloidal_cli.export_svg(cfg, svg_path)
            assert os.path.exists(svg_path)
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
                assert "<svg" in svg_content
                assert "class=\"rotor\"" in svg_content
                assert "class=\"pin\"" in svg_content
                assert "class=\"bore\"" in svg_content
                assert "class=\"drive-hole\"" in svg_content

            cycloidal_cli.export_dxf(cfg, dxf_path)
            assert os.path.exists(dxf_path)
            with open(dxf_path, "r", encoding="ascii") as f:
                dxf_content = f.read()
                assert "POLYLINE" in dxf_content
                assert "VERTEX" in dxf_content
                assert "EOF" in dxf_content

            cycloidal_cli.export_csv(cfg, csv_path)
            assert os.path.exists(csv_path)
            with open(csv_path, "r", encoding="utf-8") as f:
                csv_lines = f.readlines()
                assert csv_lines[0].strip() == "index,x,y"
                assert len(csv_lines) > 50

            cycloidal_cli.export_json(cfg, json_path)
            assert os.path.exists(json_path)
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert data["parameters"]["reduction_ratio"] == 7
                assert len(data["rotor_profile_points"]) > 50
                assert len(data["pins"]) == 8
                assert len(data["drive_holes"]) == 4

    def test_cli_execution_and_validation_flag(self):
        ret = cycloidal_cli.main(["-R", "6.0", "-N", "12", "--validate-only"])
        assert ret == 0

    def test_cli_execution_invalid_parameters(self):
        ret = cycloidal_cli.main(["-R", "-1.0", "-N", "12"])
        assert ret == 1
