from bpy.props import EnumProperty, FloatProperty
from bpy.types import Context, PropertyGroup

from ....utils import PRECISION, get_scaled_prop, set_scaled_prop


def depth_end_type_items(
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
        name="Depth End",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("depth_end", -1e-2, s),
        set=lambda s, v: set_scaled_prop("depth_end", None, 0, s, v),
    )
    depth_end_type: EnumProperty(name="Depth End", items=depth_end_type_items)
    layer_size: FloatProperty(
        name="Layer Size", default=0, min=0, precision=PRECISION, unit="LENGTH"
    )
    # ambient_type: EnumProperty(
    #     name="Ambient",
    #     items=[("OFF", "Off", ""), ("ALL", "All", ""), ("AROUND", "Around", "")],
    # )
    # curve_limit: PointerProperty(
    #     name="Curve Limit", type=Object, poll=utils.poll_curve_limit
    # )
