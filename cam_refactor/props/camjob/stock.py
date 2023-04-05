import bpy


class Stock(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name"}

    type: bpy.props.EnumProperty(
        name="Type",
        items=[("ESTIMATE", "Estimate from Job", ""), ("CUSTOM", "Custom", "")],
    )
    estimate_offset: bpy.props.FloatVectorProperty(
        name="Estimate Offset", min=0, default=(1e-3, 1e-3, 0), subtype="XYZ_LENGTH"
    )
    custom_location: bpy.props.FloatVectorProperty(
        name="Location", min=-3, max=3, default=(0, 0), size=2, subtype="XYZ_LENGTH"
    )
    custom_size: bpy.props.FloatVectorProperty(
        name="Size", min=0, default=(5e-1, 5e-1, 1e-1), subtype="XYZ_LENGTH"
    )
