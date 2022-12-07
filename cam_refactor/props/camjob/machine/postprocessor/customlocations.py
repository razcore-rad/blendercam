import bpy


class CustomLocations(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    end: bpy.props.FloatVectorProperty(name="End", default=(0, 0, 0), min=0, subtype="XYZ_LENGTH")
    start: bpy.props.FloatVectorProperty(name="Start", default=(0, 0, 0), min=0, subtype="XYZ_LENGTH")
    tool_change: bpy.props.FloatVectorProperty(name="Tool Change", default=(0, 0, 0), min=0, subtype="XYZ_LENGTH")
