from bpy.props import EnumProperty, FloatProperty
from bpy.types import PropertyGroup

from ....utils import PRECISION, get_scaled_prop, set_scaled_prop


class WorkArea(PropertyGroup):
    ICON_MAP = {"curve_limit": "OUTLINER_OB_CURVE"}
    EXCLUDE_PROPNAMES = ["name", "depth_end_type", "depth_end", "layer_size"]

    depth_end: FloatProperty(
        name="Depth End",
        precision=PRECISION,
        unit="LENGTH",
        get=lambda s: get_scaled_prop("depth_end", -1e-2, s),
        set=lambda s, v: set_scaled_prop("depth_end", None, 0, s, v),
    )
    depth_end_type: EnumProperty(
        name="Depth End",
        items=[
            ("OBJECT", "Object", ""),
            ("CUSTOM", "Custom", ""),
        ],
    )
    layer_size: FloatProperty(name="Layer Size", default=0, min=0, precision=PRECISION, unit="LENGTH")
