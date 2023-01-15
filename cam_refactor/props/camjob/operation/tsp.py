from typing import Iterator

from mathutils import Vector


def distance(v1: Vector, v2: Vector) -> float:
    return (v2 - v1).xy.length


def length(tour: list[Vector]) -> float:
    """The tour length computed from distances between each pair of consecutive points"""
    return sum(distance(tour[i], tour[i - 1]) for i in range(len(tour)))


def get_nearest_neighbor(points: Iterator[Vector], origin: Vector) -> Vector:
    return min(points, key=lambda p: distance(p, origin))


def sorted_nearest_neighbor(points: set[Vector], start=None) -> list[tuple[int, Vector]]:
    start = next(iter(points)) if start is None else start
    i = 0
    result = [(i, start)]
    unvisited = set(points - {start})
    while unvisited:
        i += 1
        p = get_nearest_neighbor(unvisited, result[-1][-1])
        result.append((i, p))
        unvisited.remove(p)
    return result


def run(points: set[Vector], start=Vector()) -> list[Vector]:
    start = get_nearest_neighbor(points, start.freeze())
    return sorted_nearest_neighbor(points, start)
