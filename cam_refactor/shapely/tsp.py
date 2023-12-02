from shapely import Geometry, Point, prepare
from shapely.ops import nearest_points
from typing import Iterator

from .ops import start_at
from ..utils import first


def distance(geom: Geometry, origin: Point) -> tuple[float, Point]:
    prepare(geom)
    p1, p2 = nearest_points(geom, origin)
    return (p1.distance(p2), p1)


def get_nearest_neighbor(geom: list[tuple[int, Geometry]], origin: Point) -> list[tuple[Geometry, Point]]:
    _, at, geom, i = min((distance(lr, origin) + (lr, i) for i, lr in geom), key=first)
    if geom.geom_type == "LinearRing":
        geom = start_at(geom, at)
    return i, geom, at


def run(geoms: Iterator[Geometry], origin: Point) -> list[Geometry]:
    result = []
    unvisited = list(enumerate(geoms))
    while unvisited:
        i, geom, origin = get_nearest_neighbor(unvisited, origin)
        result.append(geom)
        unvisited = [u for u in unvisited if first(u) != i]
    return result
