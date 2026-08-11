"""Geodesy for field-scale guidance work.

Everything a guidance line needs happens in a plane: offsetting a swath, walking
a heading, measuring a perpendicular gap between passes. Latitude/longitude is a
bad place to do that arithmetic, so each field gets its own **local transverse
Mercator** projection centred on the field itself.

Why a local tmerc and not UTM: a field near a UTM zone edge would straddle two
zones, and the scale factor at the edge of a zone is ~1/1000 (a metre per
kilometre). Re-centring on the field puts the field on the central meridian,
where the scale factor is exactly 1 and grows as (x/R)^2/2 -- about 1.5 mm per
kilometre at 5 km out. Projection error is therefore far below GNSS noise, and
the projection is conformal, so a straight line in the plane is a sensible thing
to ask a machine to drive.

The one thing to keep in mind is **grid convergence**: away from the central
meridian, grid north is not true north. The difference is roughly
``dlon * sin(lat)`` -- about 0.03 deg at 5 km east/west offset at 45 deg
latitude. Headings that leave this module (into ISOXML, into a producer-facing
report) are therefore converted back to *true* azimuth with :func:`true_azimuth`
rather than reported as the raw grid angle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from pyproj import CRS, Transformer

__all__ = [
    "WGS84_A",
    "WGS84_F",
    "LatLon",
    "LocalFrame",
    "geodesic_distance",
    "initial_bearing",
    "destination",
    "normalize_deg",
    "normalize_heading_180",
    "circular_mean_180",
    "true_azimuth",
    "polyline_length",
    "densify",
]

WGS84_A = 6378137.0
"""WGS84 semi-major axis, metres."""

WGS84_F = 1.0 / 298.257223563
"""WGS84 flattening."""

_WGS84_B = WGS84_A * (1.0 - WGS84_F)


@dataclass(frozen=True)
class LatLon:
    """A geographic position. Latitude and longitude in decimal degrees."""

    lat: float
    lon: float

    def __iter__(self):
        yield self.lat
        yield self.lon

    def as_tuple(self) -> tuple[float, float]:
        return (self.lat, self.lon)

    @classmethod
    def from_any(cls, value) -> "LatLon":
        """Accept a LatLon, a ``(lat, lon)`` pair, or a ``{"lat":..,"lon":..}``."""
        if isinstance(value, LatLon):
            return value
        if isinstance(value, dict):
            return cls(float(value["lat"]), float(value["lon"]))
        lat, lon = value
        return cls(float(lat), float(lon))


class LocalFrame:
    """A metric plane centred on one point, for one field's worth of work.

    ``x`` is grid east and ``y`` is grid north, both in metres, both zero at the
    origin. The transform is exactly invertible, so a round trip through
    :meth:`to_xy` and :meth:`to_latlon` returns the input to within floating
    point noise.
    """

    def __init__(self, origin: LatLon | tuple[float, float]):
        self.origin = LatLon.from_any(origin)
        self._crs = CRS.from_proj4(
            f"+proj=tmerc +lat_0={self.origin.lat!r} +lon_0={self.origin.lon!r} "
            "+k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
        )
        # always_xy keeps the argument order (lon, lat) / (x, y) rather than
        # letting the CRS axis order flip it, which is a classic source of
        # silently transposed coordinates.
        self._fwd = Transformer.from_crs("EPSG:4326", self._crs, always_xy=True)
        self._inv = Transformer.from_crs(self._crs, "EPSG:4326", always_xy=True)

    @classmethod
    def around(cls, points: Iterable[LatLon | tuple[float, float]]) -> "LocalFrame":
        """Build a frame centred on the mean of ``points``.

        Centring on the data keeps every coordinate close to the central
        meridian, which is where the projection is most accurate.
        """
        pts = [LatLon.from_any(p) for p in points]
        if not pts:
            raise ValueError("cannot build a local frame around zero points")
        # Longitudes are averaged as unit vectors so a field sitting on the
        # antimeridian does not average to the opposite side of the planet.
        sx = sum(math.cos(math.radians(p.lon)) for p in pts)
        sy = sum(math.sin(math.radians(p.lon)) for p in pts)
        mean_lon = math.degrees(math.atan2(sy, sx)) if (sx or sy) else pts[0].lon
        mean_lat = sum(p.lat for p in pts) / len(pts)
        return cls(LatLon(mean_lat, mean_lon))

    def to_xy(self, point: LatLon | tuple[float, float]) -> tuple[float, float]:
        p = LatLon.from_any(point)
        x, y = self._fwd.transform(p.lon, p.lat)
        return (x, y)

    def to_latlon(self, x: float, y: float) -> LatLon:
        lon, lat = self._inv.transform(x, y)
        return LatLon(lat, lon)

    def many_to_xy(
        self, points: Sequence[LatLon | tuple[float, float]]
    ) -> list[tuple[float, float]]:
        if not points:
            return []
        pts = [LatLon.from_any(p) for p in points]
        xs, ys = self._fwd.transform([p.lon for p in pts], [p.lat for p in pts])
        return list(zip(xs, ys))

    def many_to_latlon(
        self, coords: Sequence[tuple[float, float]]
    ) -> list[LatLon]:
        if not coords:
            return []
        lons, lats = self._inv.transform(
            [c[0] for c in coords], [c[1] for c in coords]
        )
        return [LatLon(lat, lon) for lat, lon in zip(lats, lons)]

    def true_azimuth_at(self, x: float, y: float, grid_azimuth_deg: float) -> float:
        """Convert a grid azimuth at ``(x, y)`` into a true (geodetic) azimuth.

        Grid convergence is measured empirically -- step one metre along grid
        north from the point and ask what geodetic bearing that step actually
        had. That is exact for any projection, with no convergence formula to
        get wrong.
        """
        here = self.to_latlon(x, y)
        north = self.to_latlon(x, y + 1.0)
        convergence = initial_bearing(here, north)
        return normalize_deg(grid_azimuth_deg + convergence)


def normalize_deg(deg: float) -> float:
    """Wrap an angle into ``[0, 360)``."""
    return deg % 360.0


def normalize_heading_180(deg: float) -> float:
    """Wrap a heading into ``[0, 180)``.

    An AB line has no inherent direction -- driving it north-east and driving it
    south-west are the same line -- so pass geometry is compared modulo 180.
    """
    return deg % 180.0


def circular_mean_180(headings_deg: Sequence[float]) -> float:
    """Mean of undirected headings, in ``[0, 180)``.

    Averaging 179 deg and 1 deg arithmetically gives 90 deg, which is wrong by a
    right angle. Doubling the angles maps the 180-degree ambiguity onto a full
    circle, where a vector mean is well defined, then halving brings it back.
    """
    if not headings_deg:
        raise ValueError("no headings to average")
    sx = sum(math.cos(2 * math.radians(h)) for h in headings_deg)
    sy = sum(math.sin(2 * math.radians(h)) for h in headings_deg)
    if abs(sx) < 1e-12 and abs(sy) < 1e-12:
        # Perfectly opposed headings have no meaningful mean; fall back to the
        # first sample rather than returning an arbitrary zero.
        return normalize_heading_180(headings_deg[0])
    return normalize_heading_180(math.degrees(math.atan2(sy, sx)) / 2.0)


def geodesic_distance(a: LatLon, b: LatLon) -> float:
    """Distance in metres on the WGS84 ellipsoid (Vincenty inverse).

    Falls back to a spherical haversine for the near-antipodal case where
    Vincenty is known not to converge; field work never hits that path, but a
    silent non-convergence would be worse than a slightly less precise number.
    """
    a = LatLon.from_any(a)
    b = LatLon.from_any(b)
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)

    u1 = math.atan((1 - WGS84_F) * math.tan(lat1))
    u2 = math.atan((1 - WGS84_F) * math.tan(lat2))
    sin_u1, cos_u1 = math.sin(u1), math.cos(u1)
    sin_u2, cos_u2 = math.sin(u2), math.cos(u2)
    dlon = lon2 - lon1

    lam = dlon
    for _ in range(200):
        sin_lam, cos_lam = math.sin(lam), math.cos(lam)
        sin_sigma = math.hypot(
            cos_u2 * sin_lam, cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lam
        )
        if sin_sigma == 0.0:
            return 0.0  # coincident points
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cos_u1 * cos_u2 * sin_lam / sin_sigma
        cos_sq_alpha = 1 - sin_alpha * sin_alpha
        cos_2sigma_m = (
            cos_sigma - 2 * sin_u1 * sin_u2 / cos_sq_alpha if cos_sq_alpha else 0.0
        )
        c = WGS84_F / 16 * cos_sq_alpha * (4 + WGS84_F * (4 - 3 * cos_sq_alpha))
        lam_prev = lam
        lam = dlon + (1 - c) * WGS84_F * sin_alpha * (
            sigma
            + c
            * sin_sigma
            * (cos_2sigma_m + c * cos_sigma * (-1 + 2 * cos_2sigma_m**2))
        )
        if abs(lam - lam_prev) < 1e-12:
            break
    else:
        return _haversine(a, b)

    u_sq = cos_sq_alpha * (WGS84_A**2 - _WGS84_B**2) / (_WGS84_B**2)
    big_a = 1 + u_sq / 16384 * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
    big_b = u_sq / 1024 * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
    delta_sigma = (
        big_b
        * sin_sigma
        * (
            cos_2sigma_m
            + big_b
            / 4
            * (
                cos_sigma * (-1 + 2 * cos_2sigma_m**2)
                - big_b
                / 6
                * cos_2sigma_m
                * (-3 + 4 * sin_sigma**2)
                * (-3 + 4 * cos_2sigma_m**2)
            )
        )
    )
    return _WGS84_B * big_a * (sigma - delta_sigma)


def _haversine(a: LatLon, b: LatLon) -> float:
    r = 6371008.8  # mean Earth radius
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def initial_bearing(a: LatLon, b: LatLon) -> float:
    """Forward azimuth from ``a`` to ``b``, degrees clockwise from true north."""
    a = LatLon.from_any(a)
    b = LatLon.from_any(b)
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlon = math.radians(b.lon - a.lon)
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return normalize_deg(math.degrees(math.atan2(y, x)))


def destination(origin: LatLon, bearing_deg: float, distance_m: float) -> LatLon:
    """Walk ``distance_m`` from ``origin`` along ``bearing_deg`` (spherical)."""
    origin = LatLon.from_any(origin)
    r = 6371008.8
    ang = distance_m / r
    brg = math.radians(bearing_deg)
    lat1, lon1 = math.radians(origin.lat), math.radians(origin.lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang) + math.cos(lat1) * math.sin(ang) * math.cos(brg)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brg) * math.sin(ang) * math.cos(lat1),
        math.cos(ang) - math.sin(lat1) * math.sin(lat2),
    )
    return LatLon(math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180)


def true_azimuth(a: LatLon, b: LatLon) -> float:
    """Alias for :func:`initial_bearing`, named for how exporters read."""
    return initial_bearing(a, b)


def polyline_length(points: Sequence[LatLon]) -> float:
    """Total geodesic length of a lat/lon polyline, metres."""
    pts = [LatLon.from_any(p) for p in points]
    return sum(geodesic_distance(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def densify(
    points: Sequence[tuple[float, float]], max_spacing_m: float
) -> list[tuple[float, float]]:
    """Insert intermediate vertices so no segment exceeds ``max_spacing_m``.

    Planar coordinates in, planar coordinates out. Curved patterns are exported
    as vertex lists, and a terminal that linearly interpolates between widely
    spaced vertices will cut the corner -- densifying bounds that error.
    """
    if max_spacing_m <= 0:
        raise ValueError("max_spacing_m must be positive")
    if len(points) < 2:
        return list(points)
    out: list[tuple[float, float]] = [points[0]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        steps = int(math.ceil(seg / max_spacing_m)) if seg > max_spacing_m else 1
        for i in range(1, steps + 1):
            t = i / steps
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out
