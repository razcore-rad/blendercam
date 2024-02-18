from collections.abc import Iterable
from shapely import Geometry, Point, LinearRing, prepare
from shapely.ops import nearest_points
from typing import Any, Callable, Iterator

from .ops import start_at
from ..utils import first


def distance(geom: Geometry, origin: Point) -> tuple[float, Point]:
    prepare(geom)
    p1, p2 = nearest_points(geom, origin)
    return (p1.distance(p2), p1)


def get_nearest_neighbor(
    geoms: list[tuple[int, Any]], origin: Point, key: Callable[[Any], Geometry]
) -> list[tuple[int, Any, Point]]:
    _, at, pack, i = min((distance(key(g), origin) + (g, i) for i, g in geoms), key=first)
    if isinstance(pack, Iterable):
        pack = tuple((start_at(x, at) if isinstance(x, LinearRing) else x) for x in pack)
    elif isinstance(pack, LinearRing):
        pack = start_at(pack, at)
    return i, pack, at


def run(iter: Iterator[Any], origin: Point, *, key: Callable[[Any], Geometry] = lambda x: x) -> list[tuple[int, Any]]:
    result = []
    unvisited = list(enumerate(iter))
    while unvisited:
        i, pack, origin = get_nearest_neighbor(unvisited, origin, key)
        result.append(pack)
        unvisited = [u for u in unvisited if first(u) != i]
    return result
