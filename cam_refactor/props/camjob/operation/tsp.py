from typing import Iterator
from mathutils import Vector


def distance(v1: Vector, v2: Vector) -> float:
    return (v2 - v1).xy.length


def get_nearest_neighbor(points: Iterator[Vector], origin: Vector) -> Vector:
    return min(points, key=lambda p: distance(p, origin))


def run(unvisited: set[Vector], origin: Vector) -> list[Vector]:
    result = []
    while unvisited:
        origin = get_nearest_neighbor(unvisited, origin)
        result.append(origin)
        unvisited.remove(origin)
    return result
