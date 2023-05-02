from itertools import chain
from math import isclose, tau
from shapely import LinearRing, Polygon, force_3d, is_ccw, union_all
from typing import Iterator

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

from . import tsp
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
from ....bmesh.ops import get_islands
from ....types import ComputeResult


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
    EXCLUDE_PROPNAMES = {
        "name",
        "computed",
        "source_type",
        "object_source",
        "collection_source",
    }

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
    EXCLUDE_PROPNAMES = {
        "name",
        "source_type",
        "curve_object_source",
        "object_source",
        "collection_source",
    }

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
    ) -> Iterator[Vector]:
        result = set()
        if operation.tool_id < 0:
            return result

        tolerance = 1 / 10**PRECISION / context.scene.unit_settings.scale_length
        for obj in self.get_evaluated_source(context):
            if obj.name not in context.view_layer.objects:
                continue

            temp_mesh = obj.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(temp_mesh)
            for island in get_islands(bm, bm.verts)["islands"]:
                vectors = [obj.matrix_world @ v.co for v in island]
                vector_mean = sum(vectors, Vector()) / len(vectors)
                vector_mean.z = max(v.z for v in vectors)
                _, diameter = get_fit_circle_2d((v.xy for v in vectors), tolerance)
                is_valid = (
                    operation.get_cutter(context).diameter <= diameter
                    and operation.get_depth_end(context) < vector_mean.z < 0.0
                )
                if is_valid:
                    result.add(vector_mean.freeze())
            bm.free()
            obj.to_mesh_clear()
        return result

    def execute_compute(
        self, context: Context, operation: PropertyGroup
    ) -> ComputeResult:
        result_execute, result_computed = set(), []
        depth_end = operation.get_depth_end(context)
        rapid_height = operation.movement.rapid_height
        layer_size = operation.work_area.layer_size
        is_layer_size_zero = isclose(layer_size, 0)
        for i, v in tsp.run(self.get_feature_positions(context, operation)):
            layers = get_layers(v.z, layer_size, depth_end)
            layers = chain(
                [rapid_height],
                layers if is_layer_size_zero else intersperse(layers, v.z),
                [rapid_height],
            )
            result_computed.extend(
                {
                    "vector": (v.x, v.y, z),
                    "rapid_height": rapid_height,
                    "dwell": self.dwell if isclose(z, depth_end) else 0.0,
                    "feed_rate": operation.feed.rate,
                    "plunge_scale": operation.feed.plunge_scale,
                    "spindle_direction": operation.spindle.direction_type,
                    "spindle_rpm": operation.spindle.rpm,
                }
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
    cut_type: EnumProperty(
        name="Cut",
        items=[
            ("ON_LINE", "On Line", "On line"),
            ("INSIDE", "Inside", "Inside"),
            ("OUTSIDE", "Outside", "Outside"),
        ],
    )
    cut_type_sign = {"INSIDE": -1, "OUTSIDE": 1}
    outlines_count: IntProperty(name="Outlines Count", default=1, min=1)
    outlines_offset: FloatProperty(name="Outlines Offset", default=0.0)
    style_type: EnumProperty(
        name="Style",
        items=[
            ("CONVENTIONAL", "Conventional", "Conventional rounded"),
            ("OVERSHOOT", "Overshoot", "Overshoot style"),
        ],
    )

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

    def execute_compute(
        self, context: Context, operation: PropertyGroup
    ) -> ComputeResult:
        # TODO
        # - outlines count and offset
        # - sort tool paths
        # - bridges
        result_execute, result_computed, polygons = set(), [], []
        _, bb_max = operation.get_bound_box(context)
        depth_end = operation.get_depth_end(context)
        if bb_max.z < depth_end:
            return ComputeResult({"CANCELLED"}, result_computed)

        uncertainty = 10 ** -(PRECISION + 1)
        for obj in self.get_evaluated_source(context):
            mesh = obj.to_mesh()
            mesh.calc_loop_triangles()
            vectors = (
                [(obj.matrix_world @ mesh.vertices[i].co).xy for i in t.vertices]
                for t in mesh.loop_triangles
                if t.area != 0.0 and obj.matrix_world @ t.normal
            )
            polygons += [
                p.buffer(uncertainty, resolution=0)
                for vs in vectors
                if len(vs) == 3 and (p := Polygon(vs)).is_valid
            ]
            obj.to_mesh_clear()
        geometry = union_all(polygons).simplify(EPSILON)
        cut_type = operation.strategy.cut_type
        if cut_type != "ON_LINE":
            geometry = geometry.buffer(
                self.cut_type_sign[cut_type] * operation.get_cutter(context).radius,
                resolution=BUFFER_RESOLUTION,
            )
        geometry = [geometry] if geometry.geom_type == "Polygon" else geometry.geoms
        exteriors = (
            e.reverse() if do_reverse(e := g.exterior, operation) else e
            for g in geometry
        )
        interiors = (
            i.reverse() if do_reverse(i, operation, is_exterior=False) else i
            for g in geometry
            for i in g.interiors
        )
        geometry = chain(exteriors, interiors)
        # geometry = chain(*([g.exterior] + list(g.interiors) for g in geometry))
        layer_size = operation.work_area.layer_size
        layers = get_layers(min(0.0, bb_max.z), layer_size, depth_end)
        geometry = [[force_3d(g, z) for z in layers] for g in geometry]
        rapid_height = operation.movement.rapid_height
        computed = {
            "rapid_height": rapid_height,
            "dwell": 0.0,
            "feed_rate": operation.feed.rate,
            "plunge_scale": operation.feed.plunge_scale,
            "spindle_direction": operation.spindle.direction_type,
            "spindle_rpm": operation.spindle.rpm,
        }
        if len(geometry) == 1:
            result_computed = [
                dict(computed, **{"vector": cs})
                for gs in geometry
                for g in gs
                for cs in g.coords
            ]
        else:
            gs2 = []
            for gs1, gs2 in zip(geometry[:-1], geometry[1:]):
                c1 = gs1[0].coords[-1]
                c2 = gs2[0].coords[0]
                result_computed.extend(
                    chain(
                        (
                            dict(computed, **{"vector": cs})
                            for g in gs1
                            for cs in g.coords
                        ),
                        [
                            dict(computed, **{"vector": (c1[0], c1[1], rapid_height)}),
                            dict(computed, **{"vector": (c2[0], c2[1], rapid_height)}),
                        ],
                    )
                )
            result_computed.extend(
                dict(computed, **{"vector": cs}) for g in gs2 for cs in g.coords
            )
        result_execute.add("FINISHED")
        return ComputeResult(
            reduce_cancelled_or_finished(result_execute), result_computed
        )


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
