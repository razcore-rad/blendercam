import bpy

from ... import utils


class WorkArea(bpy.types.PropertyGroup):
    ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}
    EXCLUDE_PROPNAMES = {"name", "depth_end_type", "depth_end", "layer_size"}

    depth_end: bpy.props.FloatProperty(
        name="Depth End", default=-1e-3, max=0, precision=utils.PRECISION, unit="LENGTH"
    )
    depth_end_type: bpy.props.EnumProperty(
        name="Depth End",
        items=(
            ("CUSTOM", "Custom", ""),
            ("SOURCE", "Source", ""),
            ("STOCK", "Stock", ""),
        ),
    )
    layer_size: bpy.props.FloatProperty(
        name="Layer Size", default=0, min=0, precision=utils.PRECISION, unit="LENGTH"
    )
    ambient_type: bpy.props.EnumProperty(
        name="Ambient",
        items=[("OFF", "Off", ""), ("ALL", "All", ""), ("AROUND", "Around", "")],
    )
    curve_limit: bpy.props.PointerProperty(
        name="Curve Limit", type=bpy.types.Object, poll=utils.poll_curve_limit
    )
