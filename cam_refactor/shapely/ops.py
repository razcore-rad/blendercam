from shapely import LinearRing, Point


def start_at(linear_ring: LinearRing, at: Point) -> LinearRing:
    result = linear_ring
    at_distance = linear_ring.project(at)
    coords = linear_ring.coords[:]
    for i, p in enumerate(coords):
        point_distance = linear_ring.project(Point(p))
        if point_distance == at_distance:
            result = LinearRing(coords[i:-1] + coords[:i + 1])
            break
        elif point_distance > at_distance:
            cp = linear_ring.interpolate(at_distance)
            result = LinearRing([(cp.x, cp.y)] + coords[i:-1] + coords[:i])
            break
    return result
