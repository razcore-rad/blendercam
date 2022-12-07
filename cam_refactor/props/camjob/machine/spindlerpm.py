import bpy


class SpindleRPM(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    default: bpy.props.IntProperty(name="Spindle RPM Default", default=5000, min=500)
    max: bpy.props.IntProperty(name="Spindle RPM Max", default=20000, min=500)
    min: bpy.props.IntProperty(name="Spindle RPM Min", default=25000, min=500)
