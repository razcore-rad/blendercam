import bpy

from . import customlocations


class PostProcessorMixin(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "custom_locations", "use_custom_locations"}

    custom_locations: bpy.props.PointerProperty(type=customlocations.CustomLocations)
    g_code_footer: bpy.props.StringProperty(
        name="G-code Footer", default="", subtype="FILE_PATH"
    )
    g_code_header: bpy.props.StringProperty(
        name="G-code Header", default="", subtype="FILE_PATH"
    )
    use_custom_locations: bpy.props.BoolProperty(name="Custom Locations", default=False)
    use_tool_definitions: bpy.props.BoolProperty(name="Tool Definitions", default=True)
    use_tool_length_offset: bpy.props.BoolProperty(
        name="Tool Length Offset", default=False
    )


class Base(PostProcessorMixin, bpy.types.PropertyGroup):
    pass


class LinuxCNC(PostProcessorMixin, bpy.types.PropertyGroup):
    use_path_blending: bpy.props.BoolProperty(name="Path Blending", default=True)
