"""Core cycloidal drive geometry, validation, and profile generation module.

Provides pure Python geometric calculations for epicycloid/hypocycloid
pin-and-rotor cycloidal speed reducers without requiring Autodesk Fusion 360
or external third-party dependencies.
"""

import math
from typing import List, Tuple, Dict, Any, Optional


def get_point(t: float, R: float, Rr: float, E: float, N: int) -> Tuple[float, float]:
    """Calculate the 2D coordinate on a cycloidal rotor tooth profile at parameter t.

    Parameters:
        t: Parameter angle in radians [0, 2*pi].
        R: Pitch circle radius of pin housing / roller centers (cm or mm).
        Rr: Roller/pin radius.
        E: Eccentricity of the cycloidal disc.
        N: Number of housing pins / rollers. Rotor has (N - 1) lobes/teeth.

    Returns:
        (x, y) coordinates on the rotor profile.
    """
    denom = (R / (E * N)) - math.cos((1.0 - N) * t)
    num = math.sin((1.0 - N) * t)
    psi = math.atan2(num, denom)

    x = (R * math.cos(t)) - (Rr * math.cos(t + psi)) - (E * math.cos(N * t))
    y = (-R * math.sin(t)) + (Rr * math.sin(t + psi)) + (E * math.cos(N * t))
    return (x, y)


def get_distance(xa: float, ya: float, xb: float, yb: float) -> float:
    """Calculate Euclidean distance between two 2D points."""
    return math.hypot(xa - xb, ya - yb)


class CycloidalDriveConfig:
    """Configuration and derived geometric parameters for a cycloidal gear drive."""

    def __init__(
        self,
        R: float,
        N: int,
        eccentricity_ratio: float = 0.5,
        rotor_thickness: float = 1.0,
        housing_thickness: Optional[float] = None,
        bore_diameter: float = 0.0,
        num_holes: int = 0,
        hole_pin_diameter: float = 0.0,
        hole_circle_diameter: float = 0.0,
        num_gears: int = 1,
    ):
        self.R = float(R)
        self.N = int(N)
        self.eccentricity_ratio = float(eccentricity_ratio)
        self.rotor_thickness = float(rotor_thickness)
        self.housing_thickness = (
            float(housing_thickness)
            if housing_thickness is not None
            else 2.0 * self.rotor_thickness
        )
        self.bore_diameter = float(bore_diameter)
        self.num_holes = int(num_holes)
        self.hole_pin_diameter = float(hole_pin_diameter)
        self.hole_circle_diameter = float(hole_circle_diameter)
        self.num_gears = int(num_gears)

    @property
    def num_lobes(self) -> int:
        """Number of teeth/lobes on the cycloidal rotor (N - 1)."""
        return self.N - 1

    @property
    def reduction_ratio(self) -> int:
        """Reduction ratio for standard single-stage housing fixed drive."""
        return self.num_lobes

    @property
    def housing_circumference(self) -> float:
        return 2.0 * self.R * math.pi

    @property
    def roller_radius(self) -> float:
        """Pin / roller radius Rr."""
        return self.housing_circumference / (4.0 * self.N)

    @property
    def eccentricity(self) -> float:
        """Shaft eccentricity E."""
        return self.eccentricity_ratio * self.roller_radius

    @property
    def max_point_dist(self) -> float:
        return 0.25 * self.roller_radius

    @property
    def min_point_dist(self) -> float:
        return 0.5 * self.max_point_dist

    def validate(self) -> List[str]:
        """Validate configuration parameters, returning list of validation error messages."""
        errors = []
        if self.R <= 0:
            errors.append(f"Housing pitch radius R must be positive, got {self.R}.")
        if self.N < 2:
            errors.append(f"Number of pins N must be at least 2, got {self.N}.")
        if self.eccentricity_ratio <= 0:
            errors.append(
                f"Eccentricity ratio must be positive, got {self.eccentricity_ratio}."
            )
        if self.rotor_thickness <= 0:
            errors.append(
                f"Rotor thickness must be positive, got {self.rotor_thickness}."
            )

        if not errors:
            # Undercut check: R / (E * N) must be > 1 to avoid profile self-intersection/cusps
            e = self.eccentricity
            if e * self.N >= self.R:
                errors.append(
                    f"Eccentricity E ({e:.4f}) * N ({self.N}) = {e*self.N:.4f} exceeds radius R ({self.R}), causing self-intersection."
                )

            # Minimum rotor radius roughly: R - Rr - E
            rr = self.roller_radius
            approx_root_r = self.R - rr - e
            if approx_root_r <= 0:
                errors.append("Roller radius and eccentricity exceed pitch radius R.")

            if self.bore_diameter < 0:
                errors.append("Bore diameter cannot be negative.")
            elif self.bore_diameter / 2.0 >= approx_root_r:
                errors.append(
                    f"Bore radius ({self.bore_diameter/2.0:.4f}) exceeds approx rotor root radius ({approx_root_r:.4f})."
                )

            if self.num_holes > 0:
                if self.hole_pin_diameter <= 0:
                    errors.append("Drive pin diameter must be positive when num_holes > 0.")
                if self.hole_circle_diameter <= 0:
                    errors.append(
                        "Hole circle diameter must be positive when num_holes > 0."
                    )
                else:
                    # Rotor hole radius is (hole_pin_diameter / 2 + E)
                    hole_r = self.hole_pin_diameter / 2.0 + e
                    hole_center_r = self.hole_circle_diameter / 2.0
                    if hole_center_r + hole_r >= approx_root_r:
                        errors.append(
                            f"Drive pin holes extend past rotor root boundary ({hole_center_r + hole_r:.4f} >= {approx_root_r:.4f})."
                        )
                    if hole_center_r - hole_r <= self.bore_diameter / 2.0:
                        errors.append(
                            f"Drive pin holes collide with central bore ({hole_center_r - hole_r:.4f} <= {self.bore_diameter/2.0:.4f})."
                        )

        return errors


def generate_single_lobe_points(config: CycloidalDriveConfig) -> List[Tuple[float, float]]:
    """Generate adaptive points for a single lobe / segment [0, 2*pi/(N-1)].

    This faithfully reproduces the adaptive resolution step used in the Fusion 360 script.
    """
    R = config.R
    Rr = config.roller_radius
    E = config.eccentricity
    N = config.N
    max_dist = config.max_point_dist
    min_dist = config.min_point_dist

    points: List[Tuple[float, float]] = []

    xs, ys = get_point(0.0, R, Rr, E, N)
    points.append((xs, ys))

    et = 2.0 * math.pi / (N - 1)
    xe, ye = get_point(et, R, Rr, E, N)
    x = xs
    y = ys
    ct = 0.0
    dt = math.pi / N

    while (math.hypot(x - xe, y - ye) > max_dist or ct < et / 2.0) and ct < et:
        xt, yt = get_point(ct + dt, R, Rr, E, N)
        dist = get_distance(x, y, xt, yt)

        ddt = dt / 2.0
        last_too_big = False
        last_too_small = False

        while dist > max_dist or dist < min_dist:
            if dist > max_dist:
                if last_too_small:
                    ddt /= 2.0
                last_too_small = False
                last_too_big = True
                if ddt > dt / 2.0:
                    ddt = dt / 2.0
                dt -= ddt
            elif dist < min_dist:
                if last_too_big:
                    ddt /= 2.0
                last_too_small = True
                last_too_big = False
                dt += ddt

            xt, yt = get_point(ct + dt, R, Rr, E, N)
            dist = get_distance(x, y, xt, yt)

        x = xt
        y = yt
        points.append((x, y))
        ct += dt

    points.append((xe, ye))
    return points


def generate_full_rotor_profile(
    config: CycloidalDriveConfig, num_samples_per_lobe: int = 50
) -> List[Tuple[float, float]]:
    """Generate a closed full 360-degree perimeter of the cycloidal rotor.

    Returns closed list of (x, y) points starting and ending at parameter t=0.
    """
    points: List[Tuple[float, float]] = []
    total_steps = (config.N - 1) * max(10, num_samples_per_lobe)
    R = config.R
    Rr = config.roller_radius
    E = config.eccentricity
    N = config.N

    for i in range(total_steps):
        t = (2.0 * math.pi * i) / total_steps
        pt = get_point(t, R, Rr, E, N)
        points.append(pt)

    # Close the curve with the starting point
    points.append(points[0])
    return points


def generate_pin_centers(config: CycloidalDriveConfig) -> List[Tuple[float, float]]:
    """Return list of (x, y) coordinates for all N housing pin centers."""
    centers = []
    R = config.R
    for i in range(config.N):
        angle = (2.0 * math.pi * i) / config.N
        centers.append((R * math.cos(angle), R * math.sin(angle)))
    return centers


def generate_drive_hole_centers(
    config: CycloidalDriveConfig,
) -> List[Tuple[float, float]]:
    """Return list of (x, y) coordinates for all rotor drive hole centers."""
    if config.num_holes <= 0:
        return []
    centers = []
    hr = config.hole_circle_diameter / 2.0
    for i in range(config.num_holes):
        angle = (2.0 * math.pi * i) / config.num_holes
        centers.append((hr * math.cos(angle), hr * math.sin(angle)))
    return centers
