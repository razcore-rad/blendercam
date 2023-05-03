from shapely import LinearRing, Point, prepare, shortest_line

from .ops import start_at
from ..utils import first


def distance(linear_ring: LinearRing, origin: Point) -> tuple[float, Point]:
    prepare(linear_ring)
    line = shortest_line(linear_ring, origin)
    if not line.is_valid:
        return (0.0, Point())
    return (line.length, Point(first(line.coords)))


def get_nearest_neighbor(
    linear_rings: list[tuple[int, LinearRing]], origin: Point
) -> list[tuple[LinearRing, Point]]:
    _, at, i, linear_ring = min(
        (distance(lr, origin) + (i, lr) for i, lr in linear_rings), key=first
    )
    # FIXME: `at` and `first(linear_ring.coords)` do not coincide for some reason
    # Need to test `shortest_line()`
    return i, start_at(linear_ring, at), at


def run(linear_rings: list[LinearRing], origin: Point) -> list[LinearRing]:
    result = []
    unvisited = list(enumerate(linear_rings))
    while unvisited:
        i, linear_ring, origin = get_nearest_neighbor(unvisited, origin)
        result.append(linear_ring)
        unvisited = [u for u in unvisited if first(u) != i]
    return result
