from itertools import chain
from math import isclose, tau
from shapely import force_3d, union_all, Polygon
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

    @property
    def source(self) -> list[Object]:
        result = getattr(self, self.source_propname)
        if self.source_type in ["OBJECT", "CURVE_OBJECT"]:
            result = [result] if result is not None else []
        elif self.source_type == "COLLECTION":
            result = (
                [o for o in result.objects if o.type in ["CURVE", "MESH"]]
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
        return [o.evaluated_get(depsgraph) for o in self.source]

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
        self,
        context: Context,
        operation: PropertyGroup,
    ) -> Iterator[Vector]:
        result = set()
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
                    operation.cutter.diameter <= diameter
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
        result_execute, result_msgs, result_computed = set(), [], []
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
            reduce_cancelled_or_finished(result_execute),
            "\n".join(result_msgs),
            result_computed,
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
    do_merge: BoolProperty(name="Merge Outlines", default=True)
    outlines_count: IntProperty(name="Outlines Count", default=0)
    offset: IntProperty(name="Offset", default=0)
    style_type: EnumProperty(
        name="Style",
        items=[
            ("CONVENTIONAL", "Conventional", "Conventional rounded"),
            ("OVERSHOOT", "Overshoot", "Overshoot style"),
        ],
    )

    def execute_compute(
        self, context: Context, operation: PropertyGroup
    ) -> ComputeResult:
        result_execute, result_vectors = set(), []
        polygons = []
        uncertainty = 10 ** -(PRECISION + 1)
        # TODO
        #  - [ ] implementation for CURVE objects because they don't have
        #        `calc_loop_triangles()`
        #  - [ ] bridges & auto-bridges
        for obj in self.get_evaluated_source(context):
            obj.data.calc_loop_triangles()
            vectors = (
                [(obj.matrix_world @ obj.data.vertices[i].co).xy for i in t.vertices]
                for t in obj.data.loop_triangles
                if t.area != 0.0 and obj.matrix_world @ t.normal
            )
            polygons += [
                p.buffer(uncertainty, resolution=0)
                for vs in vectors
                if len(vs) == 3 and (p := Polygon(vs)).is_valid
            ]
        geometry = union_all(polygons)
        cut_type = operation.strategy.cut_type
        if cut_type != "ON_LINE":
            geometry = geometry.buffer(
                self.cut_type_sign[cut_type] * operation.cutter.diameter / 2.0,
                resolution=BUFFER_RESOLUTION,
            )
        geometry = [geometry] if geometry.geom_type == "Polygon" else geometry.geoms
        geometry = chain(*([g.exterior] + list(g.interiors) for g in geometry))
        _, bound_box_max = operation.get_bound_box(context)
        depth_end = operation.get_depth_end(context)
        layer_size = operation.work_area.layer_size
        layers = get_layers(bound_box_max.z, layer_size, depth_end)
        geometry = [[force_3d(g, z) for z in layers] for g in geometry]
        if len(geometry) == 1:
            result_vectors = [cs for gs in geometry for g in gs for cs in g.coords]
        else:
            rapid_height = operation.movement.rapid_height
            for gs1, gs2 in zip(geometry[:-1], geometry[1:]):
                c1 = gs1[0].coords[-1]
                c2 = gs2[0].coords[0]
                result_vectors.extend(
                    chain(
                        (cs for g in gs1 for cs in g.coords),
                        [
                            (c1[0], c1[1], rapid_height),
                            (c2[0], c2[1], rapid_height),
                        ],
                    )
                )
            result_vectors.extend(cs for g in gs2 for cs in g.coords)

        result_execute.add("FINISHED")
        return ComputeResult(
            reduce_cancelled_or_finished(result_execute),
            "",
            result_vectors,
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
