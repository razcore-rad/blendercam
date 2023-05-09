from itertools import chain
from math import isclose, pi, tau
from shapely import (
    LinearRing,
    Polygon,
    force_3d,
    is_ccw,
    remove_repeated_points,
    union_all,
)
from typing import Iterator, Sequence

import bpy
import bmesh
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import Collection, Context, PropertyGroup, Object
from mathutils import Vector
from shapely import Point

from .tsp import run as tsp_vectors_run
from ....bmesh.ops import get_islands
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
)


BUFFER_RESOLUTION = 4
MAP_SPLINE_POINTS = {"POLY": "points", "NURBS": "points", "BEZIER": "bezier_points"}


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

        depth_end = op.get_depth_end(context)
        for obj in op.strategy.bridges:
            if not isclose(obj.location[2], depth_end):
                obj.location[2] = depth_end

            if not isclose(obj.empty_display_size, op.strategy.bridges_length):
                obj.empty_display_size = op.strategy.bridges_length

            for c in obj.children:
                if c.type == "EMPTY" and not isclose(
                    c.empty_display_size, op.strategy.bridges_height
                ):
                    obj.empty_display_size = op.strategy.bridges_height


def update_bridges_count(self, context: Context) -> None:
    if (
        self.bridges_count == 0
        and self.bridges_source is not None
        and self.bridges_source.name in bpy.data.collections
    ):
        self.remove_bridges()

    if self.bridges_count > 0:
        self.add_bridges(context)


def update_bridges_length(self, context: Context) -> None:
    for obj in self.bridges:
        obj.empty_display_size = self.bridges_length


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
        default=1e-3,
        min=1e-5,
        max=32,
        precision=PRECISION,
        unit="LENGTH",
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
        (
            "COLLECTION",
            "Collection",
            "Collection data source",
            "OUTLINER_COLLECTION",
            1,
        ),
    ]
    source_type: EnumProperty(items=source_type_items, name="Source Type")
    object_source: PointerProperty(type=Object, name="Source", poll=poll_object_source)
    collection_source: PointerProperty(
        type=Collection, name="Source", poll=poll_collection_source
    )

    @property
    def source_propname(self) -> str:
        return f"{self.source_type.lower()}_source"

    def get_source(self, context: Context) -> list[Object]:
        result = getattr(self, self.source_propname)
        if self.source_type in ["OBJECT", "CURVE_OBJECT"]:
            result = (
                [result]
                if result is not None and result.name in context.view_layer.objects
                else []
            )
        elif self.source_type == "COLLECTION":
            result = (
                [
                    o
                    for o in result.objects
                    if o.type in ["CURVE", "MESH"]
                    and o.name in context.view_layer.objects
                ]
                if result is not None
                else []
            )
        return result

    def get_feature_positions(
        self, context: Context, operation: PropertyGroup
    ) -> Iterator[Vector]:
        pass

    def get_evaluated_source(self, context: Context) -> list[Object]:
        depsgraph = context.evaluated_depsgraph_get()
        return [o.evaluated_get(depsgraph) for o in self.get_source(context)]

    def is_source(self, obj: Object) -> bool:
        collection_source = (
            [] if self.collection_source is None else self.collection_source
        )
        return obj == self.object_source or obj in collection_source


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


class CurveToPath(SourceMixin, PropertyGroup):
    EXCLUDE_PROPNAMES = [
        "name",
        "source_type",
        "curve_object_source",
        "object_source",
        "collection_source",
    ]

    source_type_items = [
        (
            "CURVE_OBJECT",
            "Object (Curve)",
            "Curve object data source",
            "OUTLINER_OB_CURVE",
            0,
        ),
        (
            "COLLECTION",
            "Collection",
            "Collection data source",
            "OUTLINER_COLLECTION",
            1,
        ),
    ]
    source_type: EnumProperty(items=source_type_items, name="Source Type")
    curve_object_source: PointerProperty(
        type=Object, name="Source", poll=poll_curve_object_source
    )

    def is_source(self, obj: Object) -> bool:
        collection_source = (
            [] if self.collection_source is None else self.collection_source
        )
        return obj == self.curve_object_source or obj in collection_source


class Drill(SourceMixin, PropertyGroup):
    dwell: FloatProperty(name="Dwell", min=0.0)

    def get_feature_positions(
        self, context: Context, operation: PropertyGroup
    ) -> set[Vector]:
        result = set()
        if operation.tool_id < 0:
            return result

        tolerance = EPSILON / context.scene.unit_settings.scale_length
        for obj in self.get_evaluated_source(context):
            if obj.name not in context.view_layer.objects:
                continue

            temp_mesh = obj.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(temp_mesh)
            for island in get_islands(bm, bm.verts)["islands"]:
                vectors = [obj.matrix_world @ v.co for v in island]
                vector_mean = sum(vectors, Vector()) / len(vectors)
                vector_mean.z = min(0.0, max(v.z for v in vectors))
                _, diameter = get_fit_circle_2d((v.xy for v in vectors), tolerance)
                is_valid = (
                    operation.get_cutter(context).diameter <= diameter
                    and operation.get_depth_end(context) < vector_mean.z
                )
                if is_valid:
                    result.add(vector_mean.freeze())
            bm.free()
            obj.to_mesh_clear()
        return result

    def execute_compute(
        self,
        context: Context,
        last_position: Vector | Sequence[float] | Iterator[float],
    ) -> ComputeResult:
        result_execute, result_computed = set(), []
        operation = context.scene.cam_job.operation
        depth_end = operation.get_depth_end(context)
        rapid_height = operation.movement.rapid_height
        layer_size = operation.work_area.layer_size
        zero = operation.zero
        last_position = Vector(last_position).freeze()
        is_layer_size_zero = isclose(layer_size, 0)
        feature_positions = self.get_feature_positions(context, operation)
        for v in tsp_vectors_run(feature_positions, last_position):
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
        return ComputeResult(
            reduce_cancelled_or_finished(result_execute), result_computed
        )


class MedialAxis(SourceMixin, PropertyGroup):
    threshold: FloatProperty(
        name="Threshold", default=1e-3, unit="LENGTH", precision=PRECISION
    )
    subdivision: FloatProperty(
        name="Subdivision", default=2e-4, unit="LENGTH", precision=PRECISION
    )
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
    pass


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
    bridges_count: IntProperty(
        name="Bridges Count", default=0, min=0, update=update_bridges_count
    )
    bridges_length: FloatProperty(
        name="Bridges Length",
        get=lambda s: get_scaled_prop("bridges_length", 3e-3, s),
        set=lambda s, v: set_scaled_prop("bridges_length", EPSILON, None, s, v),
        precision=PRECISION,
        unit="LENGTH",
        update=update_bridges_length,
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
        set=lambda s, v: set_scaled_prop("outlines_offset", 0.0, None, s, v),
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
            (
                obj
                for obj in self.bridges_source.objects
                if obj.type == "EMPTY" and obj.parent is None
            )
            if self.bridges_source is not None
            else {}
        )

    def get_outline_distance(self, cutter_radius: float, index: int) -> float:
        distance = (index - 1) * self.outlines_distance
        return self.cut_sign * (cutter_radius + distance) + self.outlines_offset

    def get_feature_positions(
        self, context: Context, operation: PropertyGroup
    ) -> Iterator[Vector]:
        result = set()
        if operation.tool_id < 0:
            return result

        bb_min, bb_max = operation.get_bound_box(context)
        depth_end = operation.get_depth_end(context)
        is_valid = bb_max.z > depth_end
        if is_valid:
            result = [
                Vector((bb_min.x, bb_min.y, depth_end)),
                Vector((bb_min.x, bb_max.y, depth_end)),
                Vector((bb_max.x, bb_max.y, depth_end)),
                Vector((bb_max.x, bb_min.y, depth_end)),
            ]
        return result

    def compute_geometry(self, context: Context) -> Iterator:
        operation = context.scene.cam_job.operation
        polygons = []
        for obj in self.get_evaluated_source(context):
            mesh = obj.to_mesh()
            polygons += [
                Polygon((obj.matrix_world @ mesh.vertices[i].co).xy for i in p.vertices)
                for p in mesh.polygons
            ]
            obj.to_mesh_clear()
        geometry = union_all(polygons)
        if self.cut_type != "ON_LINE":
            cutter_radius = operation.get_cutter(context).radius
            geometry = [
                [g] if g.geom_type == "Polygon" else g.geoms
                for i in range(1, self.outlines_count + 1)
                if not (
                    g := geometry.buffer(
                        self.get_outline_distance(cutter_radius, i),
                        resolution=BUFFER_RESOLUTION,
                    )
                ).is_empty
            ]
            geometry = set(chain(*geometry))
        else:
            geometry = {geometry} if geometry.geom_type == "Polygon" else geometry.geoms
        exteriors = (
            e.reverse() if do_reverse(e := g.exterior, operation) else e
            for g in geometry
        )
        interiors = (
            i.reverse() if do_reverse(i, operation, is_exterior=False) else i
            for g in geometry
            for i in g.interiors
        )
        return chain(exteriors, interiors)

    def execute_compute(
        self,
        context: Context,
        last_position: Vector | Sequence[float] | Iterator[float],
    ) -> ComputeResult:
        # TODO: bridges
        result_execute, result_computed = set(), []
        operation = context.scene.cam_job.operation
        _, bb_max = operation.get_bound_box(context)
        depth_end = operation.get_depth_end(context)
        if bb_max.z < depth_end:
            return ComputeResult({"CANCELLED"}, result_computed)

        geometry = self.compute_geometry(context)
        geometry = set(remove_repeated_points(g) for g in geometry)
        geometry = tsp_geometry_run(geometry, Point(last_position))
        layer_size = operation.work_area.layer_size
        layers = get_layers(min(0.0, bb_max.z), layer_size, depth_end)
        geometry = [[force_3d(g, z) for z in layers] for g in geometry]
        rapid_height = operation.movement.rapid_height
        zero = operation.zero
        if len(geometry) == 1:
            result_computed = [
                dict(zero, vector=cs) for gs in geometry for g in gs for cs in g.coords
            ]
        else:
            gs2 = []
            for gs1, gs2 in zip(geometry[:-1], geometry[1:]):
                c1 = gs1[0].coords[-1]
                c2 = gs2[0].coords[0]
                result_computed.extend(
                    chain(
                        (dict(zero, vector=cs) for g in gs1 for cs in g.coords),
                        [
                            dict(zero, vector=(c1[0], c1[1], rapid_height)),
                            dict(zero, vector=(c2[0], c2[1], rapid_height)),
                        ],
                    )
                )
            result_computed.extend(
                dict(zero, vector=cs) for g in gs2 for cs in g.coords
            )

        if result_computed:
            c1, c2 = result_computed[0]["vector"], result_computed[-1]["vector"]
            result_computed = (
                [dict(operation.zero, vector=(c1[0], c1[1], rapid_height))]
                + result_computed
                + [dict(operation.zero, vector=(c2[0], c2[1], rapid_height))]
            )
        result_execute.add("FINISHED")
        return ComputeResult(
            reduce_cancelled_or_finished(result_execute), result_computed
        )

    def add_bridges(self, context: Context) -> None:
        # TODO: place bridges at `depth_end` and keep them updated
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

        geometry = self.compute_geometry(context)
        depth_end = operation.get_depth_end(context)
        indices = range(self.bridges_count)
        suffixes = ["Length", "Height"]
        iterator = chain(
            *([(lr, i, s) for i in indices for s in suffixes] for lr in geometry)
        )
        previous_empty = None
        for lr, i, s in iterator:
            empty = bpy.data.objects.new(f"{operation.name}Bridge{s}", None)
            empty.lock_rotation = 3 * [True]
            empty.lock_scale = empty.lock_rotation
            location = 3 * (0.0,)
            if s == "Length":
                location, *_ = lr.line_interpolate_point(
                    i / self.bridges_count, True
                ).coords
                location += (depth_end,)
                empty.empty_display_type = "CIRCLE"
                empty.empty_display_size = self.bridges_length / 2
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
            for obj in self.bridges:
                for c in obj.children:
                    bpy.data.objects.remove(c)
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
