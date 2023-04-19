from itertools import chain
from math import isclose, tau
from typing import Iterator
from shapely import force_3d, union_all, Polygon

import bpy
from mathutils import Vector

from . import tsp
from ... import utils


BUFFER_RESOLUTION = 4
MAP_SPLINE_POINTS = {"POLY": "points", "NURBS": "points", "BEZIER": "bezier_points"}


def get_layers(z: float, layer_size: float, depth_end: float) -> list[float]:
    return list(utils.seq(z - layer_size, depth_end, -layer_size)) + [depth_end]


def update_object_source(
    strategy: bpy.types.PropertyGroup, context: bpy.types.Context
) -> None:
    if isinstance(strategy, Drill):
        context.scene.cam_job.operation.work_area.depth_end_type = "CUSTOM"


class DistanceAlongPathsMixin:
    distance_along_paths: bpy.props.FloatProperty(
        name="Distance Along Paths",
        default=2e-4,
        min=1e-5,
        max=32,
        precision=utils.PRECISION,
        unit="LENGTH",
    )


class DistanceBetweenPathsMixin:
    distance_between_paths: bpy.props.FloatProperty(
        name="Distance Between Paths",
        default=1e-3,
        min=1e-5,
        max=32,
        precision=utils.PRECISION,
        unit="LENGTH",
    )


class PathsAngleMixin:
    paths_angle: bpy.props.FloatProperty(
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
    source_type: bpy.props.EnumProperty(items=source_type_items, name="Source Type")
    object_source: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Source",
        poll=utils.poll_object_source,
        update=update_object_source,
    )
    collection_source: bpy.props.PointerProperty(
        type=bpy.types.Collection, name="Source"
    )

    @property
    def source_propname(self) -> str:
        return f"{self.source_type.lower()}_source"

    @property
    def source(self) -> [bpy.types.Object]:
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

    def get_evaluated_source(
        self, depsgraph: bpy.types.Depsgraph
    ) -> [bpy.types.Object]:
        return [o.evaluated_get(depsgraph) for o in self.source]

    def is_source(self, obj: bpy.types.Object) -> bool:
        collection_source = (
            [] if self.collection_source is None else self.collection_source
        )
        return obj == self.object_source or obj in collection_source


class Block(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    bpy.types.PropertyGroup,
):
    pass


class CarveProject(DistanceAlongPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    ICON_MAP = {"curve": "OUTLINER_OB_CURVE"}

    curve: bpy.props.PointerProperty(
        name="Curve", type=bpy.types.Object, poll=utils.poll_curve_object_source
    )
    depth: bpy.props.FloatProperty(
        name="Depth", default=1e-3, unit="LENGTH", precision=utils.PRECISION
    )


class Circles(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    bpy.types.PropertyGroup,
):
    pass


class Cross(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    PathsAngleMixin,
    SourceMixin,
    bpy.types.PropertyGroup,
):
    pass


class CurveToPath(SourceMixin, bpy.types.PropertyGroup):
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
    source_type: bpy.props.EnumProperty(items=source_type_items, name="Source Type")
    curve_object_source: bpy.props.PointerProperty(
        type=bpy.types.Object, name="Source", poll=utils.poll_curve_object_source
    )

    def is_source(self, obj: bpy.types.Object) -> bool:
        collection_source = (
            [] if self.collection_source is None else self.collection_source
        )
        return obj == self.curve_object_source or obj in collection_source


class Drill(SourceMixin, bpy.types.PropertyGroup):
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
    def source(self) -> [bpy.types.Object]:
        return [o for o in super().source if o.type == "CURVE"]

    def get_tsp_center(
        self,
        depsgraph: bpy.types.Depsgraph,
        cutter_diameter: float,
        tolerance=10 ** (-utils.PRECISION),
    ) -> set[Vector]:
        result = set()
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
                    if cutter_diameter <= diameter:
                        vector_mean = sum(vectors, Vector()) / len(vectors)
                        result.add(vector_mean.freeze())
                obj.to_mesh_clear()
                temp_obj.to_mesh_clear()
                bpy.data.curves.remove(temp_obj.data)
        return result

    def execute_compute(
        self, context: bpy.types.Context, operation: bpy.types.PropertyGroup
    ) -> ({str}, str, Iterator):
        result_execute, result_msgs, result_vectors = set(), [], []
        depth_end = operation.get_depth_end(context)
        bound_box_min, _ = operation.get_bound_box(context)
        cutter_diameter = operation.cutter.diameter
        if depth_end > 0 or bound_box_min.z > 0:
            return (
                {"CANCELLED"},
                (
                    f"Drill `{operation.data.name}` can't be computed."
                    " See Depth End and check Bound Box Z < 0"
                ),
                result_vectors,
            )

        free_height = operation.movement.free_height
        layer_size = operation.work_area.layer_size
        is_layer_size_zero = isclose(layer_size, 0)
        depsgraph = context.evaluated_depsgraph_get()
        for i, v in tsp.run(self.get_tsp_center(depsgraph, cutter_diameter)):
            if v.z < depth_end or v.z > 0:
                result_execute.add("CANCELLED")
                result_msgs.append(f"Drill `{operation.data.name}` skipping {v}")
                continue

            layers = get_layers(v.z, layer_size, depth_end)
            layers = chain(
                [free_height],
                layers if is_layer_size_zero else utils.intersperse(layers, v.z),
                [free_height],
            )
            result_vectors.extend((v.x, v.y, z) for z in layers)
            result_execute.add("FINISHED")

        if "CANCELLED" in result_execute:
            result_msgs.append(
                f"Drill {operation.data.name} skipped because source"
                " data has no valid points"
            )

        return (
            utils.reduce_cancelled_or_finished(result_execute),
            "\n".join(result_msgs),
            result_vectors,
        )


class MedialAxis(SourceMixin, bpy.types.PropertyGroup):
    threshold: bpy.props.FloatProperty(
        name="Threshold", default=1e-3, unit="LENGTH", precision=utils.PRECISION
    )
    subdivision: bpy.props.FloatProperty(
        name="Subdivision", default=2e-4, unit="LENGTH", precision=utils.PRECISION
    )
    do_clean_finish: bpy.props.BoolProperty(name="Clean Finish", default=True)
    do_generate_mesh: bpy.props.BoolProperty(name="Generate Mesh", default=True)


class OutlineFill(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    bpy.types.PropertyGroup,
):
    pass


class Pocket(DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class Profile(SourceMixin, bpy.types.PropertyGroup):
    cut_type: bpy.props.EnumProperty(
        name="Cut",
        items=[
            ("ON_LINE", "On Line", "On line"),
            ("INSIDE", "Inside", "Inside"),
            ("OUTSIDE", "Outside", "Outside"),
        ],
    )
    cut_type_sign = {"INSIDE": -1, "OUTSIDE": 1}
    do_merge: bpy.props.BoolProperty(name="Merge Outlines", default=True)
    outlines_count: bpy.props.IntProperty(name="Outlines Count", default=0)
    offset: bpy.props.IntProperty(name="Offset", default=0)
    style_type: bpy.props.EnumProperty(
        name="Style",
        items=[
            ("CONVENTIONAL", "Conventional", "Conventional rounded"),
            ("OVERSHOOT", "Overshoot", "Overshoot style"),
        ],
    )

    def execute_compute(
        self, context: bpy.types.Context, operation: bpy.types.PropertyGroup
    ) -> ({str}, str, Iterator):
        result_execute, result_msgs, result_vectors = set(), [], []

        polygons = []
        uncertainty = 10 ** -(utils.PRECISION + 1)
        # TODO
        #  - [ ] implementation for CURVE objects because they don't have `calc_loop_triangles()`
        #  - [ ] bridges & auto-bridges
        for obj in self.get_evaluated_source(context.evaluated_depsgraph_get()):
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
                self.cut_type_sign[cut_type] * operation.cutter.get_radius(operation.get_depth_end(context)),
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
            free_height = operation.movement.free_height
            for gs1, gs2 in zip(geometry[:-1], geometry[1:]):
                c1 = gs1[0].coords[-1]
                c2 = gs2[0].coords[0]
                result_vectors.extend(
                    chain(
                        (cs for g in gs1 for cs in g.coords),
                        [
                            (c1[0], c1[1], free_height),
                            (c2[0], c2[1], free_height),
                        ],
                    )
                )
            result_vectors.extend(cs for g in gs2 for cs in g.coords)
        result_execute.add("FINISHED")
        return (
            utils.reduce_cancelled_or_finished(result_execute),
            "\n".join(result_msgs),
            result_vectors,
        )


class Parallel(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    PathsAngleMixin,
    SourceMixin,
    bpy.types.PropertyGroup,
):
    pass


class Spiral(
    DistanceAlongPathsMixin,
    DistanceBetweenPathsMixin,
    SourceMixin,
    bpy.types.PropertyGroup,
):
    pass


class WaterlineRoughing(
    DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup
):
    distance_between_slices: bpy.props.FloatProperty(
        name="Distance Between Slices",
        default=1e-3,
        min=1e-5,
        max=32,
        precision=utils.PRECISION,
        unit="LENGTH",
    )
    fill_between_slices: bpy.props.BoolProperty(
        name="Fill Between Slices", default=True
    )
