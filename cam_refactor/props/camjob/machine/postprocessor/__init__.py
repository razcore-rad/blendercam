from bpy.props import BoolProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from . import customlocations


class PostProcessorMixin(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "custom_locations", "use_custom_locations"}

    custom_locations: PointerProperty(type=customlocations.CustomLocations)
    g_code_footer: StringProperty(name="G-code Footer", default="", subtype="FILE_PATH")
    g_code_header: StringProperty(name="G-code Header", default="", subtype="FILE_PATH")
    use_custom_locations: BoolProperty(name="Custom Locations", default=False)
    use_tool_definitions: BoolProperty(name="Tool Definitions", default=True)
    use_tool_length_offset: BoolProperty(name="Tool Length Offset", default=False)


class Base(PostProcessorMixin, PropertyGroup):
    pass


class LinuxCNC(PostProcessorMixin, PropertyGroup):
    use_path_blending: BoolProperty(name="Path Blending", default=True)
