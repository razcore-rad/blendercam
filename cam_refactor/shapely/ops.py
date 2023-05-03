from shapely import (
    LineString,
    LinearRing,
    Point,
    remove_repeated_points,
    set_coordinates,
)
from shapely.ops import split


def start_at(line_ring: LinearRing, at: Point) -> None:
    if not line_ring.is_valid:
        return line_ring

    geoms = split(LineString(line_ring), at).geoms
    coords = (c for ls in reversed(geoms) for c in ls.coords)
    set_coordinates(line_ring, remove_repeated_points(LinearRing(coords)).coords)
