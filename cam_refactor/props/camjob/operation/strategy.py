import importlib
import math

import bpy

modnames = ["utils"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f"...{modname}", __package__)) for modname in modnames}
)


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
        name="Paths Angle", default=0, min=-math.tau, max=math.tau, precision=0, subtype="ANGLE", unit="ROTATION"
    )


class SourceMixin:
    EXCLUDE_PROPNAMES = {"name", "source_type", "object_source", "collection_source"}

    source_type_items = [
        ("OBJECT", "Object", "Object data source.", "OBJECT_DATA", 0),
        ("COLLECTION", "Collection", "Collection data source", "OUTLINER_COLLECTION", 1),
    ]
    source_type: bpy.props.EnumProperty(items=source_type_items, name="Source Type")
    object_source: bpy.props.PointerProperty(type=bpy.types.Object, name="Source", poll=utils.poll_object_source)
    collection_source: bpy.props.PointerProperty(type=bpy.types.Collection, name="Source")

    @property
    def source_propname(self) -> str:
        return f"{self.source_type.lower()}_source"

    @property
    def source(self) -> bpy.types.PropertyGroup:
        return getattr(self, self.source_propname, None)

    @property
    def is_source_valid(self) -> bool:
        return self.source is not None


class BlockStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class CarveProjectStrategy(DistanceAlongPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    ICON_MAP = {"curve": "OUTLINER_OB_CURVE"}

    curve: bpy.props.PointerProperty(name="Curve", type=bpy.types.Object, poll=utils.poll_curve_object_source)
    depth: bpy.props.FloatProperty(name="Depth", default=1e-3, unit="LENGTH", precision=utils.PRECISION)


class CirclesStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class CrossStrategy(
    DistanceAlongPathsMixin, DistanceBetweenPathsMixin, PathsAngleMixin, SourceMixin, bpy.types.PropertyGroup
):
    pass


class CurveToPathStrategy(SourceMixin, bpy.types.PropertyGroup):
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


class DrillStrategy(SourceMixin, bpy.types.PropertyGroup):
    method_type: bpy.props.EnumProperty(
        name="Method",
        items=[
            ("POINTS", "Points", "Drill at every point", "SNAP_VERTEX", 0),
            (
                "CENTER",
                "Center",
                "Position is at the center of disjoint mesh or curve islands",
                "SNAP_FACE_CENTER",
                1,
            ),
        ],
    )


class MedialAxisStrategy(SourceMixin, bpy.types.PropertyGroup):
    threshold: bpy.props.FloatProperty(name="Threshold", default=1e-3, unit="LENGTH", precision=utils.PRECISION)
    subdivision: bpy.props.FloatProperty(name="Subdivision", default=2e-4, unit="LENGTH", precision=utils.PRECISION)
    do_clean_finish: bpy.props.BoolProperty(name="Clean Finish", default=True)
    do_generate_mesh: bpy.props.BoolProperty(name="Generate Mesh", default=True)


class OutlineFillStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class PocketStrategy(DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class ProfileStrategy(SourceMixin, bpy.types.PropertyGroup):
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


class ParallelStrategy(
    DistanceAlongPathsMixin, DistanceBetweenPathsMixin, PathsAngleMixin, SourceMixin, bpy.types.PropertyGroup
):
    pass


class SpiralStrategy(DistanceAlongPathsMixin, DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    pass


class WaterlineRoughingStrategy(DistanceBetweenPathsMixin, SourceMixin, bpy.types.PropertyGroup):
    distance_between_slices: bpy.props.FloatProperty(
        name="Distance Between Slices", default=1e-3, min=1e-5, max=32, precision=utils.PRECISION, unit="LENGTH"
    )
    fill_between_slices: bpy.props.BoolProperty(name="Fill Between Slices", default=True)
