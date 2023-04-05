import bpy

from . import strategy
from ... import utils


def get_depth_end_type_items(workarea: bpy.types.PropertyGroup, context: bpy.types.Context) -> [(str, str, str)]:
    result = []
    if isinstance(context.scene.cam_job.operation.strategy, strategy.Drill):
        method_type = context.scene.cam_job.operation.strategy.method_type
        result.append(
            ("CUSTOM", "Custom", "")
            if method_type != "SEGMENTS"
            else ("VARIABLE", "Variable", "")
        )
    else:
        result.extend(
            (("CUSTOM", "Custom", ""), ("SOURCE", "Source", ""), ("STOCK", "Stock", ""))
        )
    return result


class WorkArea(bpy.types.PropertyGroup):
    ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}
    EXCLUDE_PROPNAMES = {"name", "depth_end_type", "depth_end", "layer_size"}

    depth_end: bpy.props.FloatProperty(
        name="Depth End", default=-1e-3, max=0, precision=utils.PRECISION, unit="LENGTH"
    )
    depth_end_type: bpy.props.EnumProperty(
        name="Depth End", items=get_depth_end_type_items
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
