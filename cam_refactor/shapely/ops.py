from shapely import (
    LineString,
    LinearRing,
    Point,
    remove_repeated_points,
)
from shapely.ops import split


def start_at(line_ring: LinearRing, at: Point) -> LinearRing:
    if not line_ring.is_valid:
        return line_ring

    geoms = split(LineString(line_ring), at).geoms
    coords = (c for ls in reversed(geoms) for c in ls.coords)
    return remove_repeated_points(LinearRing(coords))
