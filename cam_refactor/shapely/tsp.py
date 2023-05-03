from typing import Iterator

from shapely import Geometry, Point
from shapely.ops import prepare, shortest_line

from .ops import start_at
from ..utils import first


def distance(g1: Geometry, g2: Geometry) -> list:
    prepare(g1)
    line = shortest_line(g1, g2)
    return [line.length, Point(line.coords[0]), g1]


def get_nearest_neighbor(geoms: Iterator[Geometry], origin: Point) -> list:
    _, *result = min((distance(g, origin) for g in geoms), key=first)
    start_at(*result)
    return result


def sorted_nearest_neighbor(geoms: set[Geometry], start=None) -> list[Geometry]:
    start = first(geoms) if start is None else start
    result = [start]
    unvisited = set(geoms - {start})
    while unvisited:
        geom = get_nearest_neighbor(unvisited, result[-1].coords[0])
        result.append(geom)
        unvisited.remove(geom)
    return result


def run(geoms: set[Geometry], start=Point((0, 0))) -> list[Geometry]:
    if not geoms:
        return []
    *_, start = get_nearest_neighbor(geoms, start)
    return sorted_nearest_neighbor(geoms, start)
