import importlib

import bpy

mods = {".strategy", "...utils"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})


def get_depth_end_type_items(
    workarea: bpy.types.PropertyGroup, context: bpy.types.Context
) -> list[tuple[str, str, str]]:
    result = [("CUSTOM", "Custom", "")]
    if not isinstance(context.scene.cam_job.operation.strategy, strategy.Drill):
        result.append(("SOURCE", "Source", ""))
    result.append(("STOCK", "Stock", ""))
    return result


class WorkArea(bpy.types.PropertyGroup):
    ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}
    EXCLUDE_PROPNAMES = {"name", "depth_end_type", "depth_end", "layer_size"}

    depth_end: bpy.props.FloatProperty(
        name="Depth End", default=0, min=-1, max=0, precision=utils.PRECISION, unit="LENGTH"
    )
    depth_end_type: bpy.props.EnumProperty(name="Depth End", items=get_depth_end_type_items)
    layer_size: bpy.props.FloatProperty(
        name="Layer Size", default=0, min=0, max=1e-1, precision=utils.PRECISION, unit="LENGTH"
    )
    ambient_type: bpy.props.EnumProperty(
        name="Ambient", items=[("OFF", "Off", ""), ("ALL", "All", ""), ("AROUND", "Around", "")]
    )
    curve_limit: bpy.props.PointerProperty(name="Curve Limit", type=bpy.types.Object, poll=utils.poll_curve_limit)
