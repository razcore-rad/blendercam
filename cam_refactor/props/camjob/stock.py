from bpy.props import EnumProperty, FloatVectorProperty
from bpy.types import PropertyGroup

from ...utils import get_scaled_prop, set_scaled_prop


class Stock(PropertyGroup):
    EXCLUDE_PROPNAMES = ["name"]

    type: EnumProperty(
        name="Type",
        items=[("ESTIMATE", "Estimate from Job", ""), ("CUSTOM", "Custom", "")],
    )
    estimate_offset: FloatVectorProperty(
        name="Estimate Offset",
        subtype="XYZ_LENGTH",
        get=lambda s: get_scaled_prop("estimate_offset", (1e-3, 1e-3, 0), s),
        set=lambda s, v: set_scaled_prop("estimate_offset", 0, None, s, v),
    )
    custom_position: FloatVectorProperty(
        name="Position", default=(0, 0), size=2, subtype="XYZ_LENGTH"
    )
    custom_size: FloatVectorProperty(
        name="Size",
        subtype="XYZ_LENGTH",
        get=lambda s: get_scaled_prop("custom_size", (5e-1, 5e-1, 1e-1), s),
        set=lambda s, v: set_scaled_prop("custom_size", 0, None, s, v),
    )
