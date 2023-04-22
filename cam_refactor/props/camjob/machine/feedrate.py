from bpy.props import FloatProperty
from bpy.types import PropertyGroup


class FeedRate(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}
    default: FloatProperty(
        name="Feed Rate Default", default=1.5, min=1e-3, max=2, unit="LENGTH"
    )
    max: FloatProperty(name="Feed Rate Max", default=2, min=1e-3, max=2, unit="LENGTH")
    min: FloatProperty(
        name="Feed Rate Min", default=1e-3, min=1e-3, max=2, unit="LENGTH"
    )
