import importlib
import random
from typing import Iterator

from mathutils import Vector

mods = {"...utils"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})


def distance(v1: Vector, v2: Vector) -> float:
    return (v2 - v1).xy.length


def sample(population, samples: int, seed=42):
    """Return a list of `samples` elements sampled from `population`. Set `random.seed` with `seed`."""
    result = population
    if samples < (result_len := len(result)):
        random.seed(result_len * samples * seed)
        result = random.sample(result, samples)
    return result


def length(tour: list[Vector]) -> float:
    """The tour length computed from distances between each pair of consecutive points"""
    return sum(distance(tour[i], tour[i - 1]) for i in range(len(tour)))


def shortest(tours: list[list[Vector]]) -> float:
    """Return the tour with minimum length"""
    return min(tours, key=length)


def nearest_neighbor(points: Iterator[Vector], origin: Vector) -> Vector:
    return min(points, key=lambda p: distance(p, origin))


def sorted_nearest_neighbor(points: set[Vector], start=None) -> list[Vector]:
    start = next(iter(points)) if start is None else start
    result = [start]
    unvisited = set(points - {start})
    while unvisited:
        p = nearest_neighbor(unvisited, result[-1])
        result.append(p)
        unvisited.remove(p)
    return result


def reverse_segment_if_better(tour: list[Vector], i: int, j: int) -> None:
    """If reversing `tour[i:j]` would make the tour shorter do it."""
    # Given tour [...A-B...C-D...], consider reversing [B...C] to get [...A-C...B-D...]
    a, b, c, d = tour[i - 1], tour[i], tour[j - 1], tour[j % len(tour)]
    # Are old edges (AB + CD) longer than new ones (AC + BD)? If so, reverese segment.
    if distance(a, b) + distance(c, d) > distance(a, c) + distance(b, d):
        tour[i:j] = reversed(tour[i:j])


def all_segments(n: int) -> list[tuple[Vector, Vector]]:
    """Return `(start, end)` pairs of indices that form segments of tour of length `n`."""
    return [(start, start + length) for length in range(n, 1, -1) for start in range(n - length + 1)]


def alter(tour: list[Vector]) -> list[Vector]:
    original_length = length(tour)
    for (start, end) in all_segments(len(tour)):
        reverse_segment_if_better(tour, start, end)
    if length(tour) < original_length:
        return alter(tour)
    return tour


def run(points: set[Vector], repetitions=10) -> list[Vector]:
    return shortest([alter(sorted_nearest_neighbor(points, p)) for p in sample(points, repetitions)])
