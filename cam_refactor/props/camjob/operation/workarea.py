import importlib

import bpy

modnames = ["utils"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f"...{modname}", __package__)) for modname in modnames}
)


class WorkArea(bpy.types.PropertyGroup):
    ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}
    EXCLUDE_PROPNAMES = {"name", "depth_start", "depth_end_type", "depth_end"}

    depth_start: bpy.props.FloatProperty(
        name="Depth Start", default=0, min=0, max=1, precision=utils.PRECISION, unit="LENGTH"
    )
    depth_end_type: bpy.props.EnumProperty(
        name="Depth End",
        items=[
            ("CUSTOM", "Custom", ""),
            ("OBJECT", "Object", ""),
            ("STOCK", "Stock", ""),
        ],
    )
    depth_end: bpy.props.FloatProperty(
        name="Depth End", default=1e-1, min=1e-5, max=1, precision=utils.PRECISION, unit="LENGTH"
    )
    layer_size: bpy.props.FloatProperty(
        name="Layer Size", default=0, min=1e-4, max=1e-1, precision=utils.PRECISION, unit="LENGTH"
    )
    ambient_type: bpy.props.EnumProperty(
        name="Ambient", items=[("OFF", "Off", ""), ("ALL", "All", ""), ("AROUND", "Around", "")]
    )
    curve_limit: bpy.props.PointerProperty(name="Curve Limit", type=bpy.types.Object, poll=utils.poll_curve_limit)
