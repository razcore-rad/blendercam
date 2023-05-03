from typing import Iterator
from mathutils import Vector

from ....utils import first


def distance(v1: Vector, v2: Vector) -> float:
    return (v2 - v1).xy.length


def get_nearest_neighbor(points: Iterator[Vector], origin: Vector) -> Vector:
    return min(points, key=lambda p: distance(p, origin))


def sorted_nearest_neighbor(points: set[Vector], start=None) -> list[Vector]:
    start = first(points) if start is None else start
    result = [start]
    unvisited = set(points - {start})
    while unvisited:
        p = get_nearest_neighbor(unvisited, result[-1])
        result.append(p)
        unvisited.remove(p)
    return result


def run(points: set[Vector], start=Vector()) -> list[Vector]:
    if not points:
        return []
    start = get_nearest_neighbor(points, start.freeze())
    return sorted_nearest_neighbor(points, start)
