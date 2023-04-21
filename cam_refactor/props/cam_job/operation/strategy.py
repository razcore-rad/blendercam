from itertools import chain
from math import isclose, tau
from shapely import force_3d, union_all, Polygon

import bpy
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
from .... import utils
from ....types import ComputeResult


BUFFER_RESOLUTION = 4
MAP_SPLINE_POINTS = {"POLY": "points", "NURBS": "points", "BEZIER": "bezier_points"}


def get_layers(z: float, layer_size: float, depth_end: float) -> list[float]:
    return list(utils.seq(z - layer_size, depth_end, -layer_size)) + [depth_end]


def update_object_source(strategy: PropertyGroup, context: Context) -> None:
    if isinstance(strategy, Drill):
        context.scene.cam_job.operation.work_area.depth_end_type = "CUSTOM"


class DistanceAlongPathsMixin:
    distance_along_paths: FloatProperty(
        name="Distance Along Paths",
        default=2e-4,
        min=1e-5,
        max=32,
        precision=utils.PRECISION,
        unit="LENGTH",
    )


class DistanceBetweenPathsMixin:
    distance_between_paths: FloatProperty(
        name="Distance Between Paths",
        default=1e-3,
        min=1e-5,
        max=32,
        precision=utils.PRECISION,
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
    object_source: PointerProperty(
        type=Object,
        name="Source",
        poll=utils.poll_object_source,
        update=update_object_source,
    )
    collection_source: PointerProperty(type=Collection, name="Source")

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

    def get_source_valid_features(
        self,
        context: Context,
        operation: PropertyGroup,
    ) -> dict:
        raise NotImplementedError()

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

    curve: PointerProperty(
        name="Curve", type=Object, poll=utils.poll_curve_object_source
    )
    depth: FloatProperty(
        name="Depth", default=1e-3, unit="LENGTH", precision=utils.PRECISION
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
        type=Object, name="Source", poll=utils.poll_curve_object_source
    )

    def is_source(self, obj: Object) -> bool:
        collection_source = (
            [] if self.collection_source is None else self.collection_source
        )
        return obj == self.curve_object_source or obj in collection_source


class Drill(SourceMixin, PropertyGroup):
    source_type_items = [
        ("OBJECT", "Object", "Object data source.", "OUTLINER_OB_CURVE", 0),
        (
            "COLLECTION",
            "Collection",
            "Collection data source",
            "OUTLINER_COLLECTION",
            1,
        ),
    ]

    @property
    def source(self) -> [Object]:
        return [o for o in super().source if o.type == "CURVE"]

    def get_source_valid_features(
        self,
        context: Context,
        operation: PropertyGroup,
    ) -> dict:
        result = {"center": [], "bound_box": []}
        tolerance = 10 ** (-utils.PRECISION)
        depsgraph = context.evaluated_depsgraph_get()
        for obj in self.source:
            obj_data = obj.data
            for index in range(len(obj.data.splines)):
                temp_obj = obj.evaluated_get(depsgraph).copy()
                temp_obj.data = temp_obj.data.copy()
                for temp_spline in chain(
                    temp_obj.data.splines[:index], temp_obj.data.splines[index + 1:]
                ):
                    temp_obj.data.splines.remove(temp_spline)
                obj.data = temp_obj.data
                temp_mesh = obj.to_mesh()
                obj.data = obj_data
                if len(temp_mesh.vertices) > 0:
                    vectors = [temp_obj.matrix_world @ v.co for v in temp_mesh.vertices]
                    _, diameter = utils.get_fit_circle_2d(vectors, tolerance)
                    if operation.cutter.diameter <= diameter:
                        vector_mean = sum(vectors, Vector()) / len(vectors)
                        result["center"].append(vector_mean.freeze())
                        result["bound_box"].append(utils.get_bound_box(vectors))
                obj.to_mesh_clear()
                temp_obj.to_mesh_clear()
                bpy.data.curves.remove(temp_obj.data)
        return result

    def execute_compute(
        self, context: Context, operation: PropertyGroup
    ) -> ComputeResult:
        result_execute, result_msgs, result_vectors = set(), [], []
        depth_end = operation.get_depth_end(context)
        bound_box_min, _ = operation.get_bound_box(context)
        if depth_end > 0 or bound_box_min.z > 0:
            return (
                {"CANCELLED"},
                (
                    f"Drill `{operation.name}` can't be computed."
                    " See Depth End and check Bound Box Z < 0"
                ),
                result_vectors,
            )

        rapid_height = operation.movement.rapid_height
        layer_size = operation.work_area.layer_size
        is_layer_size_zero = isclose(layer_size, 0)
        source_valid_features = self.get_source_valid_features(context, operation)
        for i, v in tsp.run(source_valid_features["center"]):
            if v.z < depth_end or v.z > 0:
                result_execute.add("CANCELLED")
                result_msgs.append(f"Drill `{operation.name}` skipping {v}")
                continue

            layers = get_layers(v.z, layer_size, depth_end)
            layers = chain(
                [rapid_height],
                layers if is_layer_size_zero else utils.intersperse(layers, v.z),
                [rapid_height],
            )
            result_vectors.extend((v.x, v.y, z) for z in layers)
            result_execute.add("FINISHED")

        if "CANCELLED" in result_execute:
            result_msgs.append(
                f"Drill {operation.name} skipped because source"
                " data has no valid points"
            )

        return ComputeResult(
            utils.reduce_cancelled_or_finished(result_execute),
            "\n".join(result_msgs),
            result_vectors,
        )


class MedialAxis(SourceMixin, PropertyGroup):
    threshold: FloatProperty(
        name="Threshold", default=1e-3, unit="LENGTH", precision=utils.PRECISION
    )
    subdivision: FloatProperty(
        name="Subdivision", default=2e-4, unit="LENGTH", precision=utils.PRECISION
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
        uncertainty = 10 ** -(utils.PRECISION + 1)
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
                self.cut_type_sign[cut_type]
                * operation.cutter.get_radius(operation.get_depth_end(context)),
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
            utils.reduce_cancelled_or_finished(result_execute),
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
        precision=utils.PRECISION,
        unit="LENGTH",
    )
    fill_between_slices: BoolProperty(name="Fill Between Slices", default=True)
