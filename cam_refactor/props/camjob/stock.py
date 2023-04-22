from bpy.props import EnumProperty, FloatVectorProperty
from bpy.types import PropertyGroup


class Stock(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    type: EnumProperty(
        name="Type",
        items=[("ESTIMATE", "Estimate from Job", ""), ("CUSTOM", "Custom", "")],
    )
    estimate_offset: FloatVectorProperty(
        name="Estimate Offset", min=0, default=(1e-3, 1e-3, 0), subtype="XYZ_LENGTH"
    )
    custom_position: FloatVectorProperty(
        name="Position", min=-3, max=3, default=(0, 0), size=2, subtype="XYZ_LENGTH"
    )
    custom_size: FloatVectorProperty(
        name="Size", min=0, default=(5e-1, 5e-1, 1e-1), subtype="XYZ_LENGTH"
    )
