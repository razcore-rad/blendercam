import importlib
from itertools import chain
from math import isclose, tau
from typing import Iterator

import bpy
from mathutils import Vector

mods = {".tsp", "...utils"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})

MAP_SPLINE_POINTS = {"POLY": "points", "NURBS": "points", "BEZIER": "bezier_points"}


def get_drill_items(strategy: bpy.types.PropertyGroup, _context: bpy.types.Context) -> [(str, str, str, str, int)]:
    result = [("POINTS", "Points", "Drill at every point", "SNAP_VERTEX", 0)]
    if strategy.source_type == "OBJECT" and all(o.type == "CURVE" for o in strategy.source):
        result.extend(
            (
                (
                    "CENTER",
                    "Center",
                    "Position is at the center of disjoint mesh or curve islands",
                    "SNAP_FACE_CENTER",
                    1,
                ),
                ("SEGMENTS", "Segments", "Position is at the top point and depth from bottom point", "SNAP_EDGE", 2),
            )
        )
    return result


def update_object_source(strategy: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    if isinstance(strategy, Drill):
        context.scene.cam_job.operation.work_area.depth_end_type = "CUSTOM"
        if (
            strategy.source_type == "OBJECT"
            and strategy.object_source is not None
            and strategy.object_source.type == "MESH"
        ):
            strategy.method_type = "POINTS"


def update_source_type(strategy: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    if isinstance(strategy, Drill) and strategy.source_type == "COLLECTION":
        strategy.method_type = "POINTS"


def update_method_type(strategy: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    if isinstance(strategy, Drill) and strategy.method_type == "SEGMENTS":
        context.scene.cam_job.operation.work_area.depth_end_type = "VARIABLE"


def get_drill_tsp_points(source: Iterator[bpy.types.Object], depsgraph: bpy.types.Depsgraph) -> {Vector}:
    def get_vertices(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> Iterator[bpy.types.MeshVertex]:
        result = obj.to_mesh(depsgraph=depsgraph).vertices.values()
        obj.to_mesh_clear()
        return result

    return {(o.matrix_world @ v.co).freeze() for o in source for v in get_vertices(o, depsgraph)}


def get_drill_tsp_center(source: Iterator[bpy.types.Object], depsgraph: bpy.types.Depsgraph) -> {Vector}:
    result = set()
    for obj in source:
        for index in range(len(obj.data.splines)):
            temp_obj = obj.evaluated_get(depsgraph).copy()
            temp_obj.data = temp_obj.data.copy()
            for temp_spline in chain(temp_obj.data.splines[:index], temp_obj.data.splines[index + 1:]):
                temp_obj.data.splines.remove(temp_spline)
            temp_obj.data.splines.active = utils.first(temp_obj.data.splines)
            temp_mesh = obj.to_mesh()
            if len(temp_mesh.vertices) > 0:
                vector_mean = sum((v.co for v in temp_mesh.vertices), Vector()) / len(temp_mesh.vertices)
                result.add((temp_obj.matrix_world @ vector_mean).freeze())
            temp_obj.to_mesh_clear()
            bpy.data.curves.remove(temp_obj.data)
    return result


def get_drill_tsp_segments(source: Iterator[bpy.types.Object], depsgraph: bpy.types.Depsgraph) -> {Vector}:
    result = {
        (o.matrix_world @ max(getattr(s, MAP_SPLINE_POINTS[s.type]), key=lambda p: p.co.z).co).freeze()
        for o in source
        for s in o.evaluated_get(depsgraph).data.splines
    }
    if len(result) < 2:
        result = set()
    return result


TSP_FUNCS = {"POINTS": get_drill_tsp_points, "CENTER": get_drill_tsp_center, "SEGMENTS": get_drill_tsp_segments}


class DistanceAlongPathsMixin:
    distance_along_paths: bpy.props.FloatProperty(
        name="Distance Along Paths", default=2e-4, min=1e-5, max=32, precision=utils.PRECISION, unit="LENGTH"
    )


class DistanceBetweenPathsMixin:
    distance_between_paths: bpy.props.FloatProperty(
        name="Distance Between Paths", default=1e-3, min=1e-5, max=32, precision=utils.PRECISION, unit="LENGTH"
    )


class PathsAngleMixin:
    paths_angle: bpy.props.FloatProperty(
        name="Paths Angle", default=0, min=-tau, max=tau, precision=0, subtype="ANGLE", unit="ROTATION"
    )


class SourceMixin:
    EXCLUDE_PROPNAMES = {"name", "computed", "source_type", "object_source", "collection_source"}

    source_type_items = [
        ("OBJECT", "Object", "Object data source.", "OBJECT_DATA", 0),
        ("COLLECTION", "Collection", "Collection data source", "OUTLINER_COLLECTION", 1),
    ]
    source_type: bpy.props.EnumProperty(items=source_type_items, name="Source Type", update=update_source_type)
    object_source: bpy.props.PointerProperty(
        type=bpy.types.Object, name="Source", poll=utils.poll_object_source, update=update_object_source
    )
    collection_source: bpy.props.PointerProperty(type=bpy.types.Collection, name="Source")

    @property
    def source_propname(self) -> str:
        return f"{self.source_type.lower()}_source"

    @property
    def source(self) -> [bpy.types.Object]:
        result = getattr(self, self.source_propname)
        if self.source_type in ["OBJECT", "CURVE_OBJECT"]:
            result = [result] if result is not None else []
        elif self.source_type == "COLLECTION":
            result = [o for o in result.objects if o.type in ["CURVE", "MESH"]] if result is not None else []
        return result

    def get_evaluated_source(self, depsgraph: bpy.types.Depsgraph) -> [bpy.types.Object]:
        return [o.evaluated_get(depsgraph) for o in self.source]

    def is_source(self, obj: bpy.types.Object) -> bool:
        collection_source = [] if self.collection_source is None else self.collection_source
        return obj == self.object_source or obj in collection_source


class Block(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class CarveProject(DistanceAlongPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    ICON_MAP = {"curve": "OUTLINER_OB_CURVE"}

    curve: bpy.props.PointerProperty(name="Curve", type=bpy.types.Object, poll=utils.poll_curve_object_source)
    depth: bpy.props.FloatProperty(name="Depth", default=1e-3, unit="LENGTH", precision=utils.PRECISION)


class Circles(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class Cross(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, PathsAngleMixin, SourceMixin, bpy.types.PropertyGroup):
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
        ("CURVE_OBJECT", "Object (Curve)", "Curve object data source", "OUTLINER_OB_CURVE", 0),
        ("COLLECTION", "Collection", "Collection data source", "OUTLINER_COLLECTION", 1),
    ]
    source_type: bpy.props.EnumProperty(items=source_type_items, name="Source Type")
    curve_object_source: bpy.props.PointerProperty(
        type=bpy.types.Object, name="Source", poll=utils.poll_curve_object_source
    )

    def is_source(self, obj: bpy.types.Object) -> bool:
        collection_source = [] if self.collection_source is None else self.collection_source
        return obj == self.curve_object_source or obj in collection_source


class Drill(SourceMixin, bpy.types.PropertyGroup):
    method_type: bpy.props.EnumProperty(name="Method", items=get_drill_items)

    def execute_compute(self, context: bpy.types.Context, operation: bpy.types.PropertyGroup) -> ({str}, str, [Vector]):
        result_execute, result_msgs, result_vectors = set(), [], []
        depth_end = operation.get_depth_end(context)
        _, bound_box_max = operation.get_bound_box(context)
        if (self.method_type != "SEGMENTS" and isclose(depth_end, 0) or depth_end > 0) or bound_box_max.z > 0:
            return (
                {"CANCELLED"},
                f"Drill `{operation.data.name}` can't be computed. See Depth End and check Bound Box Z < 0",
                result_vectors,
            )

        free_height = operation.movement.free_height
        layer_size = operation.work_area.layer_size
        is_layer_size_zero = isclose(layer_size, 0)
        layers = list(utils.seq(-layer_size, depth_end, -layer_size)) + [depth_end]
        layers = [free_height, depth_end, free_height] if is_layer_size_zero else layers
        depsgraph = context.evaluated_depsgraph_get()
        tour = tsp.run(TSP_FUNCS[self.method_type](self.source, depsgraph))
        for i, v in tour:
            do_skip = False
            z = v.z
            if self.method_type == "SEGMENTS":
                obj, spline = [(o, s) for o in self.get_evaluated_source(depsgraph) for s in o.data.splines][i]
                points = getattr(spline, MAP_SPLINE_POINTS[spline.type])
                do_skip = len(points) != 2
                if not do_skip:
                    z = depth_end = (obj.matrix_world @ min(points, key=lambda p: p.co.z).co).z
                    layers = list(utils.seq(-layer_size, depth_end, -layer_size)) + [depth_end]
                    layers = [free_height, depth_end, free_height] if is_layer_size_zero else layers

            do_skip = do_skip or z < depth_end
            if do_skip:
                result_execute.add("CANCELLED")
                result_msgs.append(f"Drill `{operation.data.name}` can't compute {v}")
                continue

            computed_layers = chain([free_height], utils.intersperse(layers, v.z), [free_height])
            computed_layers = layers if is_layer_size_zero else computed_layers
            result_vectors.extend(Vector((v.x, v.y, z)) for z in computed_layers)
            result_execute.add("FINISHED")

        if len(tour) == 0:
            result_msgs.append(f"Drill {operation.data.name} skipped because source data has no valid points")
        return utils.reduce_cancelled_or_finished(result_execute), "\n".join(result_msgs), result_vectors


class MedialAxis(SourceMixin, bpy.types.PropertyGroup):
    threshold: bpy.props.FloatProperty(name="Threshold", default=1e-3, unit="LENGTH", precision=utils.PRECISION)
    subdivision: bpy.props.FloatProperty(name="Subdivision", default=2e-4, unit="LENGTH", precision=utils.PRECISION)
    do_clean_finish: bpy.props.BoolProperty(name="Clean Finish", default=True)
    do_generate_mesh: bpy.props.BoolProperty(name="Generate Mesh", default=True)


class OutlineFill(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
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


class Parallel(
    DistanceAlongPathsMixin, DistanceBetweenPathsMixin, PathsAngleMixin, SourceMixin, bpy.types.PropertyGroup
):
    pass


class Spiral(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class WaterlineRoughing(DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    distance_between_slices: bpy.props.FloatProperty(
        name="Distance Between Slices", default=1e-3, min=1e-5, max=32, precision=utils.PRECISION, unit="LENGTH"
    )
    fill_between_slices: bpy.props.BoolProperty(name="Fill Between Slices", default=True)
