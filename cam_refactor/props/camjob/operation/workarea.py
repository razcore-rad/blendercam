from bpy.props import EnumProperty, FloatProperty, PointerProperty
from bpy.types import Context, Object, PropertyGroup

from .... import utils


def get_depth_end_types(
    work_area: PropertyGroup, context: Context
) -> list[tuple[str, str, str]]:
    result = [("CUSTOM", "Custom", "")]
    if not context.scene.cam_job.operation.strategy_type == "DRILL":
        result += [
            ("SOURCE", "Source", ""),
        ]
    result += [("STOCK", "Stock", "")]
    return result


class WorkArea(PropertyGroup):
    ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}
    EXCLUDE_PROPNAMES = {"name", "depth_end_type", "depth_end", "layer_size"}

    depth_end: FloatProperty(
        name="Depth End", default=-1e-3, max=0, precision=utils.PRECISION, unit="LENGTH"
    )
    depth_end_type: EnumProperty(name="Depth End", items=get_depth_end_types)
    layer_size: FloatProperty(
        name="Layer Size", default=0, min=0, precision=utils.PRECISION, unit="LENGTH"
    )
    ambient_type: EnumProperty(
        name="Ambient",
        items=[("OFF", "Off", ""), ("ALL", "All", ""), ("AROUND", "Around", "")],
    )
    curve_limit: PointerProperty(
        name="Curve Limit", type=Object, poll=utils.poll_curve_limit
    )
