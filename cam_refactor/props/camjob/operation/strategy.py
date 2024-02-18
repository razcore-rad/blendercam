from itertools import chain, tee
from math import isclose, pi, tau
from operator import itemgetter
from typing import Iterator, Sequence

import bpy
import bmesh
import numpy as np
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import Collection, Context, PropertyGroup, Object
from mathutils import Vector
from shapely import (
    Geometry,
    LinearRing,
    LineString,
    Point,
    Polygon,
    force_3d,
    is_ccw,
    remove_repeated_points,
    union_all,
    get_coordinates,
    intersects,
)
from shapely.ops import split

from .tsp import run as tsp_vectors_run
from ....bmesh.ops import get_sorted_islands
from ....shapely.tsp import run as tsp_geometry_run
from ....types import ComputeResult
from ....utils import (
    EPSILON,
    PRECISION,
    get_fit_circle_2d,
    get_scaled_prop,
    intersperse,
    poll_curve_object_source,
    poll_collection_source,
    poll_object_source,
    reduce_cancelled_or_finished,
    seq,
    set_scaled_prop,
    sign,
)


BUFFER_RESOLUTION = 4


def do_reverse(g: LinearRing, operation: PropertyGroup, is_exterior=True) -> bool:
    g_is_ccw = is_ccw(g)
    return not (
        (
            is_exterior
            and operation.movement.type == "CLIMB"
            and (
                (operation.spindle.direction_type == "CW" and not g_is_ccw)
                or (operation.spindle.direction_type == "CCW" and g_is_ccw)
            )
        )
        or (
            not is_exterior
            and operation.movement.type == "CLIMB"
            and (
                (operation.spindle.direction_type == "CW" and g_is_ccw)
                or (operation.spindle.direction_type == "CCW" and not g_is_ccw)
            )
        )
        or (
            is_exterior
            and operation.movement.type == "CONVENTIONAL"
            and (
                (operation.spindle.direction_type == "CW" and g_is_ccw)
                or (operation.spindle.direction_type == "CCW" and not g_is_ccw)
            )
        )
        or (
            not is_exterior
            and operation.movement.type == "CONVENTIONAL"
            and (
                (operation.spindle.direction_type == "CW" and not g_is_ccw)
                or (operation.spindle.direction_type == "CCW" and g_is_ccw)
            )
        )
    )


def get_raw_profile_geom(operation: PropertyGroup, obj: Object) -> Polygon:
    result = Polygon()
    mesh = obj.to_mesh()
    geom = [Polygon((obj.matrix_world @ mesh.vertices[i].co).xy for i in p.vertices) for p in mesh.polygons]
    geom = union_all(geom)
    if geom.geom_type == "Polygon":
        result = remove_repeated_points(geom)
    obj.to_mesh_clear()
    return result


def get_layers(z: float, layer_size: float, depth_end: float) -> list[float]:
    return list(seq(z - layer_size, depth_end, -layer_size)) + [depth_end]


def update_bridges() -> None:
    context = bpy.context
    if not context.scene.cam_jobs:
        return

    operations = context.scene.cam_job.operations
    for op in (op for op in operations if op.strategy_type == "PROFILE"):
        if op.strategy.bridges_source is None and op.strategy.bridges_count != 0:
            op.strategy.bridges_count = 0

        if op.strategy.bridges_count == 0:
            continue

        depth_end = op.get_depth_end(context)
        for obj in op.strategy.bridges:
            if not isclose(obj.location[2], depth_end):
                obj.location[2] = depth_end

            if not isclose(obj.empty_display_size, op.strategy.bridges_radius):
                obj.empty_display_size = op.strategy.bridges_radius

            for c in obj.children:
                if c.type == "EMPTY" and not isclose(c.empty_display_size, op.strategy.bridges_height):
                    obj.empty_display_size = op.strategy.bridges_height


def update_bridges_count(self, context: Context) -> None:
    if self.bridges_count == 0 and self.bridges_source is not None and self.bridges_source.name in bpy.data.collections:
        self.remove_bridges()

    if self.bridges_count > 0:
        self.add_bridges(context)


def update_bridges_radius(self, context: Context) -> None:
    for obj in self.bridges:
        obj.empty_display_size = self.bridges_radius


def update_bridges_height(self, context: Context) -> None:
    for obj in (c for obj in self.bridges for c in obj.children if c is not None):
        obj.empty_display_size = self.bridges_height


class DistanceAlongPathsMixin:
    distance_along_paths: FloatProperty(
        name="Distance Along Paths",
        default=2e-4,
        min=1e-5,
        max=32,
        precision=PRECISION,
        unit="LENGTH",
    )


class DistanceBetweenPathsMixin:
    distance_between_paths: FloatProperty(
        name="Distance Between Paths",
        default=5,
        min=0.1,
        max=100,
        precision=1,
        subtype="PERCENTAGE",
    )


class PathsAngleMixin:
    paths_angle: FloatProperty(
        name="Paths Angle",
        default=0,
        min=-tau,
        max=tau,
        precision=0,
        subtype="ANGLE",
        unit="ROTATION",
    )


class SourceMixin:
    EXCLUDE_PROPNAMES = [
        "name",
        "computed",
        "source_type",
        "object_source",
        "collection_source",
    ]

    source_type_items = [
        ("OBJECT", "Object", "Object data source.", "OBJECT_DATA", 0),
        ("COLLECTION", "Collection", "Collection data source", "OUTLINER_COLLECTION", 1),
    ]
    source_type: EnumProperty(items=source_type_items, name="Source Type")
    object_source: PointerProperty(type=Object, name="Source", poll=poll_object_source)
    collection_source: PointerProperty(type=Collection, name="Source", poll=poll_collection_source)

    @property
    def source_propname(self) -> str:
        return f"{self.source_type.lower()}_source"

    def is_source(self, obj: Object) -> bool:
        collection_source = [] if self.collection_source is None else self.collection_source
        return obj == self.object_source or obj in collection_source

    def is_valid(self, bb: tuple[Vector, Vector], depth_end: float, rapid_height: float) -> bool:
        return all(isclose(v.z, depth_end) or depth_end < v.z < rapid_height for v in bb)

    def get_source(self, context: Context) -> list[Object]:
        result = getattr(self, self.source_propname)
        if self.source_type in ["OBJECT", "CURVE_OBJECT"]:
            result = [result] if result is not None and result.name in context.view_layer.objects else []
        elif self.source_type == "COLLECTION":
            result = (
                [o for o in result.objects if o.type in ["CURVE", "MESH"] and o.name in context.view_layer.objects]
                if result is not None
                else []
            )
        return result

    def get_feature_positions(self, context: Context, operation: PropertyGroup) -> Iterator[Vector]:
        result = set()
        if operation.tool_id < 0:
            return result

        bb_min, bb_max = operation.get_bound_box(context)
        depth_end = operation.get_depth_end(context)
        rapid_height = operation.movement.rapid_height
        if self.is_valid((bb_min, bb_max), depth_end, rapid_height):
            result = [
                Vector((bb_min.x, bb_min.y, depth_end)),
                Vector((bb_min.x, bb_max.y, depth_end)),
                Vector((bb_max.x, bb_max.y, depth_end)),
                Vector((bb_max.x, bb_min.y, depth_end)),
            ]
        return result

    def get_evaluated_source(self, context: Context) -> list[Object]:
        depsgraph = context.evaluated_depsgraph_get()
        return [o.evaluated_get(depsgraph) for o in self.get_source(context)]

    def get_bound_box(self, obj: Object) -> tuple[Vector, Vector]:
        vectors = (obj.matrix_world @ Vector(c) for c in obj.bound_box)
        return tuple(Vector(f(cs) for cs in zip(*ps)) for f, ps in zip((min, max), tee(vectors)))

    def get_depth_end(self, context: Context, operation: PropertyGroup, obj: Object = None) -> float:
        result = float("-inf")
        depth_end_type = operation.work_area.depth_end_type
        if depth_end_type == "OBJECT":
            bb_min, _ = self.get_bound_box(obj)
            result = bb_min.z
        elif operation.work_area.depth_end_type == "CUSTOM":
            result = operation.work_area.depth_end
        return result

    def get_profiles(self, context: Context, operation: PropertyGroup) -> list[tuple[Object, Polygon]]:
        return [
            (obj, geom)
            for obj in self.get_evaluated_source(context)
            if not (geom := get_raw_profile_geom(operation, obj)).is_empty
        ]


class Block(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    PropertyGroup,
):
    pass


class CarveProject(DistanceAlongPathsMixin, SourceMixin, PropertyGroup):
    ICON_MAP = {"curve": "OUTLINER_OB_CURVE"}

    curve: PointerProperty(name="Curve", type=Object, poll=poll_curve_object_source)
    depth: FloatProperty(
        name="Depth",
        unit="LENGTH",
        precision=PRECISION,
        get=lambda s: get_scaled_prop("depth", 1e-3, s),
        set=lambda s, v: set_scaled_prop("depth", None, None, s, v),
    )


class Circles(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    PropertyGroup,
):
    pass


class Cross(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    PathsAngleMixin,
    SourceMixin,
    PropertyGroup,
):
    pass


class ObjectToPath(SourceMixin, PropertyGroup):
    EXCLUDE_PROPNAMES = [
        "name",
        "source_type",
        "curve_object_source",
        "object_source",
        "collection_source",
    ]

    def execute_compute(
        self,
        context: Context,
        operation: PropertyGroup,
        last_position: Vector | Sequence[float] | Iterator[float],
    ) -> ComputeResult:
        result_computed = []
        rapid_height = operation.movement.rapid_height
        zero = operation.zero
        for obj in self.get_evaluated_source(context):
            temp_mesh = obj.to_mesh()
            if obj.name not in context.view_layer.objects or len(temp_mesh.vertices) == 0:
                obj.to_mesh_clear()
                continue

            vertices = temp_mesh.vertices
            c1, c2 = [(obj.matrix_world @ v.co)[:2] + (rapid_height,) for v in [vertices[0], vertices[-1]]]
            result_computed.append(dict(zero, vector=c1))
            result_computed.extend(dict(zero, vector=obj.matrix_world @ v.co) for v in vertices)
            result_computed.append(dict(zero, vector=c2))
            obj.to_mesh_clear()
        return ComputeResult({"FINISHED"}, result_computed)


class Drill(SourceMixin, PropertyGroup):
    source_type_items = [
        ("OBJECT", "Object", "Object data source.", "OBJECT_DATA", 0),
        (
            "COLLECTION",
            "Collection",
            "Collection data source",
            "OUTLINER_COLLECTION",
            1,
        ),
    ]
    source_type: EnumProperty(items=source_type_items, name="Source Type")

    dwell: FloatProperty(name="Dwell", min=0.0)

    def get_feature_positions(self, context: Context, operation: PropertyGroup) -> dict[Vector, float]:
        result = {}
        if operation.tool_id < 0:
            return result

        tolerance = EPSILON / context.scene.unit_settings.scale_length
        cutter_diameter = operation.get_cutter(context).diameter
        rapid_height = operation.movement.rapid_height

        for obj in self.get_evaluated_source(context):
            if obj.name not in context.view_layer.objects:
                continue

            temp_mesh = obj.to_mesh()
            vectors = [obj.matrix_world @ v.co for v in temp_mesh.vertices]
            circle_position, circle_diameter = get_fit_circle_2d((v.xy for v in vectors), tolerance)
            circle_position = circle_position.resized(3)
            circle_position.z = max(v.z for v in vectors)

            bb = self.get_bound_box(obj)
            depth_end = self.get_depth_end(context, operation, obj)
            if self.is_valid(bb, depth_end, rapid_height) and (
                cutter_diameter < circle_diameter or isclose(cutter_diameter, circle_diameter)
            ):
                result[circle_position.freeze()] = depth_end
            obj.to_mesh_clear()
        return result

    def execute_compute(
        self,
        context: Context,
        operation: PropertyGroup,
        last_position: Vector | Sequence[float] | Iterator[float],
    ) -> ComputeResult:
        result_execute, result_computed = set(), []
        rapid_height = operation.movement.rapid_height
        layer_size = operation.work_area.layer_size
        zero = operation.zero
        last_position = Vector(last_position).freeze()
        is_layer_size_zero = isclose(layer_size, 0)
        features = self.get_feature_positions(context, operation)
        positions = features.keys()
        for v in tsp_vectors_run(set().union(positions), last_position):
            depth_end = features[v]
            layers = get_layers(v.z, layer_size, depth_end)
            layers = chain(
                [rapid_height],
                layers if is_layer_size_zero else intersperse(layers, v.z),
                [rapid_height],
            )
            result_computed.extend(
                dict(
                    zero,
                    vector=(v.x, v.y, z),
                    dwell=self.dwell if isclose(z, depth_end) else 0.0,
                )
                for z in layers
            )
        result_execute.add("FINISHED")
        return ComputeResult(reduce_cancelled_or_finished(result_execute), result_computed)


class MedialAxis(SourceMixin, PropertyGroup):
    threshold: FloatProperty(name="Threshold", default=1e-3, unit="LENGTH", precision=PRECISION)
    subdivision: FloatProperty(name="Subdivision", default=2e-4, unit="LENGTH", precision=PRECISION)
    do_clean_finish: BoolProperty(name="Clean Finish", default=True)
    do_generate_mesh: BoolProperty(name="Generate Mesh", default=True)


class OutlineFill(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    PropertyGroup,
):
    pass


class Pocket(DistanceBetweenPathsMixin, SourceMixin, PropertyGroup):
    def execute_compute(
        self,
        context: Context,
        operation: PropertyGroup,
        last_position: Vector | Sequence[float] | Iterator[float],
    ) -> ComputeResult:
        result_computed = []

        layer_size = operation.work_area.layer_size
        cutter_radius = (cutter_diameter := operation.get_cutter(context).diameter) / 2
        rapid_height = operation.movement.rapid_height
        zero = operation.zero

        profiles = self.get_profiles(context, operation)
        geoms = tsp_geometry_run(profiles, Point(last_position), key=itemgetter(1))
        for obj, geom in geoms:
            if obj.name not in context.view_layer.objects:
                continue

            bb_min, bb_max = (bb := self.get_bound_box(obj))
            depth_end = self.get_depth_end(context, operation, obj)
            if not self.is_valid(bb, depth_end, rapid_height):
                return ComputeResult({"CANCELLED"}, result_computed)

            linear_rings = []
            temp_geom = geom.buffer(cutter_radius, resolution=BUFFER_RESOLUTION)
            index = 1
            while not temp_geom.is_empty:
                temp_geom = geom.buffer(
                    -index * self.distance_between_paths / 100 * cutter_diameter, resolution=BUFFER_RESOLUTION
                )
                if temp_geom.geom_type == "Polygon":
                    linear_rings.extend(temp_geom.interiors)
                    linear_rings.append(temp_geom.exterior)
                elif temp_geom.geom_type == "MultiPolygon":
                    linear_rings.extend(g.exterior for g in temp_geom.geoms)
                index += 1

            linear_rings = tsp_geometry_run(
                [lr.reverse() if do_reverse(lr, operation) else lr for lr in linear_rings if not lr.is_empty],
                Point(last_position),
            )

            layers = get_layers(bb_max.z, layer_size, depth_end)
            for layer_index, layer in enumerate(layers):
                for linear_ring_index in range(len(linear_rings)):
                    linear_ring = linear_rings[linear_ring_index if layer_index % 2 == 0 else (-1 - linear_ring_index)]
                    linear_ring_coordinates = get_coordinates(linear_ring)
                    if layer_index == 0 and linear_ring_index == 0:
                        result_computed.append(dict(zero, vector=np.append(linear_ring_coordinates[0], rapid_height)))
                    line = LineString([last_position[:2], linear_ring.coords[0]])
                    is_line_intersection = any(intersects(line, p) for p in geom.interiors)
                    result_computed.extend(dict(zero, vector=np.append(cs, layer)) for cs in linear_ring_coordinates)
                    if linear_ring_index > 0 and is_line_intersection:
                        result_computed.extend(dict(zero, vector=np.append(x, rapid_height)) for x in line.coords)
                    last_position = result_computed[-1]["vector"]
            result_computed.append(dict(zero, vector=np.append(last_position[:2], rapid_height)))
        return ComputeResult({"FINISHED"}, result_computed)


class Profile(SourceMixin, PropertyGroup):
    EXCLUDE_PROPNAMES = [
        "name",
        "computed",
        "source_type",
        "object_source",
        "collection_source",
        "style_type",
        "bridges_source",
    ]

    cut_type: EnumProperty(
        name="Cut",
        items=[
            ("ON_LINE", "On Line", "On line"),
            ("INSIDE", "Inside", "Inside"),
            ("OUTSIDE", "Outside", "Outside"),
        ],
    )
    cut_type_sign = {"ON_LINE": 0, "INSIDE": -1, "OUTSIDE": 1}
    bridges_source: PointerProperty(type=Collection)
    bridges_count: IntProperty(name="Bridges Count", default=0, min=0, update=update_bridges_count)
    bridges_radius: FloatProperty(
        name="Bridges Radius",
        get=lambda s: get_scaled_prop("bridges_radius", 3e-3, s),
        set=lambda s, v: set_scaled_prop("bridges_radius", EPSILON, None, s, v),
        precision=PRECISION,
        unit="LENGTH",
        update=update_bridges_radius,
    )
    bridges_height: FloatProperty(
        name="Bridges Height",
        get=lambda s: get_scaled_prop("bridges_height", 1e-3, s),
        set=lambda s, v: set_scaled_prop("bridges_height", EPSILON, None, s, v),
        precision=PRECISION,
        unit="LENGTH",
        update=update_bridges_height,
    )
    outlines_count: IntProperty(name="Outlines Count", default=1, min=1)
    outlines_offset: FloatProperty(
        name="Outlines Offset",
        get=lambda s: get_scaled_prop("outlines_offset", 0.0, s),
        set=lambda s, v: set_scaled_prop("outlines_offset", None, None, s, v),
        precision=PRECISION,
        unit="LENGTH",
    )
    outlines_distance: FloatProperty(
        name="Outlines Distance",
        get=lambda s: get_scaled_prop("outlines_distance", 3e-3, s),
        set=lambda s, v: set_scaled_prop("outlines_distance", EPSILON, None, s, v),
        precision=PRECISION,
        unit="LENGTH",
    )
    style_type: EnumProperty(
        name="Style",
        items=[
            ("CONVENTIONAL", "Conventional", "Conventional rounded"),
            ("OVERSHOOT", "Overshoot", "Overshoot style"),
        ],
    )

    @property
    def cut_sign(self) -> int:
        return self.cut_type_sign[self.cut_type]

    @property
    def bridges(self) -> Iterator[Object]:
        return (
            (obj for obj in self.bridges_source.objects if obj.type == "EMPTY" and obj.parent is None)
            if self.bridges_source is not None
            else {}
        )

    def get_outline_distance(self, cutter_radius: float, index: int) -> float:
        distance = (index - 1) * self.outlines_distance
        return self.cut_sign * (cutter_radius + distance) + self.outlines_offset

    def get_profiles(self, context: Context, operation: PropertyGroup) -> list[tuple[Object, LinearRing]]:
        result = []
        profiles = super().get_profiles(context, operation)
        cutter_radius = operation.get_cutter(context).radius
        for obj, geom in profiles:
            if self.cut_type != "ON_LINE":
                geoms = {
                    g
                    for i in range(1, self.outlines_count + 1)
                    if not (
                        g := geom.buffer(self.get_outline_distance(cutter_radius, i), resolution=BUFFER_RESOLUTION)
                    ).is_empty
                }
            else:
                geoms = {geom}
            exteriors = (e.reverse() if do_reverse(e := g.exterior, operation) else e for g in geoms)
            interiors = (
                i.reverse() if do_reverse(i, operation, is_exterior=False) else i for g in geoms for i in g.interiors
            )
            result.extend((obj, g) for g in chain(exteriors, interiors))
        return result

    def bridge_geometry(self, geom: Geometry, bridges: Geometry, z: float, depth_end_bridges: float) -> Geometry:
        if not bridges:
            return geom

        result = geom
        even_odd = 0 if bridges.contains(Point(geom.coords[0][:2])) else 1
        if z < depth_end_bridges:
            geom = LineString(geom.coords)
            splits = split(geom, bridges).geoms
            result = LineString(
                (cs[0], cs[1], depth_end_bridges) if i % 2 == even_odd else cs
                for i, g in enumerate(splits)
                for cs in g.coords
            )
        return result

    def execute_compute(
        self,
        context: Context,
        operation: PropertyGroup,
        last_position: Vector | Sequence[float] | Iterator[float],
    ) -> ComputeResult:
        result_computed = []

        layer_size = operation.work_area.layer_size
        rapid_height = operation.movement.rapid_height
        zero = operation.zero

        bridges = union_all([Point(b.location[:2]).buffer(self.bridges_radius) for b in self.bridges])
        profiles = self.get_profiles(context, operation)
        geoms = tsp_geometry_run(profiles, Point(last_position), key=itemgetter(1))
        for obj, geom in geoms:
            if obj.name not in context.view_layer.objects:
                continue

            bb_min, bb_max = (bb := self.get_bound_box(obj))
            depth_end = self.get_depth_end(context, operation, obj)
            if not self.is_valid(bb, depth_end, rapid_height):
                return ComputeResult({"CANCELLED"}, result_computed)

            depth_end_bridges = min(bb_max.z, depth_end + self.bridges_height)
            layers = get_layers(bb_max.z, layer_size, depth_end)
            depth_geoms = [self.bridge_geometry(force_3d(geom, z), bridges, z, depth_end_bridges) for z in layers]
            c1, c2 = [c[:2] + (rapid_height,) for c in (geom.coords[0], geom.coords[-1])]
            result_computed.append(dict(zero, vector=c1))
            result_computed.extend(dict(zero, vector=cs) for g in depth_geoms for cs in g.coords)
            result_computed.append(dict(zero, vector=c2))
        return ComputeResult({"FINISHED"}, result_computed)

    def add_bridges(self, context: Context) -> None:
        cam_job = context.scene.cam_job
        operation = cam_job.operation

        cam_job.add_data(context)
        col_name = f"{operation.name}Bridges"
        col = bpy.data.collections.get(col_name)
        if col is None:
            col = bpy.data.collections.new(col_name)
        if col.name not in cam_job.data.children:
            cam_job.data.children.link(col)
        self.bridges_source = col
        for obj in col.objects:
            bpy.data.objects.remove(obj)

        depth_end = operation.get_depth_end(context)
        profiles = self.get_profiles(context, operation)
        indices = range(self.bridges_count)
        suffixes = ["Radius", "Height"]
        iterator = chain(*([(lr, i, s) for i in indices for s in suffixes] for _, lr in profiles))
        previous_empty = None
        for lr, i, s in iterator:
            empty = bpy.data.objects.new(f"{operation.name}Bridge{s}", None)
            empty.lock_rotation = 3 * [True]
            empty.lock_scale = empty.lock_rotation
            location = 3 * (0.0,)
            if s == "Radius":
                location, *_ = lr.line_interpolate_point(i / self.bridges_count, True).coords
                location += (depth_end,)
                empty.empty_display_type = "CIRCLE"
                empty.empty_display_size = self.bridges_radius
                empty.rotation_euler[0] = pi / 2
                empty.lock_location[2] = True
            else:
                empty.empty_display_type = "SINGLE_ARROW"
                empty.empty_display_size = self.bridges_height
                empty.rotation_euler[0] = -pi / 2
                empty.lock_location = empty.lock_rotation
                empty.parent = previous_empty
            empty.location = location
            col.objects.link(empty)
            previous_empty = empty

    def remove_bridges(self) -> None:
        if self.bridges_source is not None:
            for obj in self.bridges_source.objects:
                bpy.data.objects.remove(obj)
            bpy.data.collections.remove(self.bridges_source)


class Parallel(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    PathsAngleMixin,
    SourceMixin,
    PropertyGroup,
):
    pass


class Spiral(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    PropertyGroup,
):
    pass


class WaterlineRoughing(DistanceBetweenPathsMixin, SourceMixin, PropertyGroup):
    distance_between_slices: FloatProperty(
        name="Distance Between Slices",
        default=1e-3,
        min=1e-5,
        max=32,
        precision=PRECISION,
        unit="LENGTH",
    )
    fill_between_slices: BoolProperty(name="Fill Between Slices", default=True)
