from bpy.props import IntProperty
from bpy.types import PropertyGroup


class SpindleRPM(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    default: IntProperty(name="Spindle RPM Default", default=5000, min=500)
    max: IntProperty(name="Spindle RPM Max", default=20000, min=500)
    min: IntProperty(name="Spindle RPM Min", default=25000, min=500)
