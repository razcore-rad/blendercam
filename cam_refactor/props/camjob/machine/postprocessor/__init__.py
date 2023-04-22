from bpy.props import BoolProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from .custompositions import CustomPositions


class PostProcessorMixin(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "custom_positions", "use_custom_positions"}

    custom_positions: PointerProperty(type=CustomPositions)
    g_code_footer: StringProperty(name="G-code Footer", default="", subtype="FILE_PATH")
    g_code_header: StringProperty(name="G-code Header", default="", subtype="FILE_PATH")
    use_custom_positions: BoolProperty(name="Custom Positions", default=False)
    use_tool_definitions: BoolProperty(name="Tool Definitions", default=True)
    use_tool_length_offset: BoolProperty(name="Tool Length Offset", default=False)


class Base(PostProcessorMixin, PropertyGroup):
    pass


class LinuxCNC(PostProcessorMixin, PropertyGroup):
    use_path_blending: BoolProperty(name="Path Blending", default=True)
