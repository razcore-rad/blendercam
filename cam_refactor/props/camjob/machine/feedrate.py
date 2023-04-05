import bpy


class FeedRate(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}
    default: bpy.props.FloatProperty(
        name="Feed Rate Default", default=1.5, min=1e-3, max=2, unit="LENGTH"
    )
    max: bpy.props.FloatProperty(
        name="Feed Rate Max", default=2, min=1e-3, max=2, unit="LENGTH"
    )
    min: bpy.props.FloatProperty(
        name="Feed Rate Min", default=1e-3, min=1e-3, max=2, unit="LENGTH"
    )

