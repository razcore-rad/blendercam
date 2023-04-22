from bpy.props import FloatVectorProperty
from bpy.types import PropertyGroup


class CustomPositions(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    end: FloatVectorProperty(name="End", default=(0, 0, 0), min=0, subtype="XYZ_LENGTH")
    start: FloatVectorProperty(
        name="Start", default=(0, 0, 0), min=0, subtype="XYZ_LENGTH"
    )
    tool_change: FloatVectorProperty(
        name="Tool Change", default=(0, 0, 0), min=0, subtype="XYZ_LENGTH"
    )
