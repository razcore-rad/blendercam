from shapely import LinearRing, Point, prepare
from shapely.ops import nearest_points

from .ops import start_at
from ..utils import first


def distance(linear_ring: LinearRing, origin: Point) -> tuple[float, Point]:
    prepare(linear_ring)
    p1, p2 = nearest_points(linear_ring, origin)
    return (p1.distance(p2), p1)


def get_nearest_neighbor(
    linear_rings: list[tuple[int, LinearRing]], origin: Point
) -> list[tuple[LinearRing, Point]]:
    _, at, linear_ring, i = min(
        (distance(lr, origin) + (lr, i) for i, lr in linear_rings), key=first
    )
    return i, start_at(linear_ring, at), at


def run(linear_rings: list[LinearRing], origin: Point) -> list[LinearRing]:
    result = []
    unvisited = list(enumerate(linear_rings))
    while unvisited:
        i, linear_ring, origin = get_nearest_neighbor(unvisited, origin)
        result.append(linear_ring)
        unvisited = [u for u in unvisited if first(u) != i]
    return result
