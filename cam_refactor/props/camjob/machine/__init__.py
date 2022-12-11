import importlib

import bpy

mods = {".feedrate", ".postprocessor", ".spindlerpm"}

globals().update({mod.lstrip("."): importlib.reload(importlib.import_module(mod, __package__)) for mod in mods})


def update_post_processor(machine: bpy.types.PropertyGroup, context: bpy.types.Context) -> None:
    post_processor_dict = {
        "ANILAM": postprocessor.Base,
        "CENTROID": postprocessor.Base,
        "FADAL": postprocessor.Base,
        "GRAVOS": postprocessor.Base,
        "GRBL": postprocessor.Base,
        "ISO": postprocessor.Base,
        "HAFCO_HM_50": postprocessor.Base,
        "HEIDENHAIN": postprocessor.Base,
        "HEIDENHAIN_530": postprocessor.Base,
        "HEIDENHAIN_TNC151": postprocessor.Base,
        "LINUX_CNC": postprocessor.LinuxCNC,
        "LYNX_OTTER_O": postprocessor.Base,
        "MACH3": postprocessor.Base,
        "SHOPBOT_MTC": postprocessor.Base,
        "SIEGKX1": postprocessor.Base,
        "WIN_PC": postprocessor.Base,
    }
    previous_post_processor = machine.post_processor
    Machine.post_processor = bpy.props.PointerProperty(type=post_processor_dict[machine.post_processor_enum])
    utils.copy(context, previous_post_processor, machine.post_processor)


class Machine(bpy.types.PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "post_processor_enum"}

    work_space: bpy.props.FloatVectorProperty(
        name="Work Space", default=(8e-1, 5.6e-1, 9e-2), min=0, subtype="XYZ_LENGTH"
    )
    feed_rate: bpy.props.PointerProperty(type=feedrate.FeedRate)
    spindle_rpm: bpy.props.PointerProperty(type=spindlerpm.SpindleRPM)
    axes: bpy.props.IntProperty(name="Axes", default=3, min=3, max=5)
    post_processor_enum: bpy.props.EnumProperty(
        name="Post Processor",
        default="GRBL",
        items=[
            ("ANILAM", "Anilam Crusader M", "Post processor for Anilam Crusader M"),
            ("CENTROID", "Centroid M40", "Post processor for Centroid M40"),
            ("FADAL", "Fadal", "Post processor for Fadal VMC"),
            ("GRAVOS", "Gravos", "Post processor for Gravos"),
            ("GRBL", "grbl", "Post processor for grbl firmware on Arduino with CNC shield"),
            ("ISO", "Iso", "Standardized G-code ISO 6983 (RS-274)"),
            ("HAFCO_HM_50", "Hafco HM-50", "Post processor for Hafco HM-50"),
            ("HEIDENHAIN", "Heidenhain", "Post processor for Heidenhain"),
            ("HEIDENHAIN_530", "Heidenhain 530", "Post processor for Heidenhain 530"),
            ("HEIDENHAIN_TNC151", "Heidenhain TNC151", "Post processor for Heidenhain TNC151"),
            ("LINUX_CNC", "LinuxCNC", "Post processor for Linux based CNC control software"),
            ("LYNX_OTTER_O", "Lynx Otter O", "Post processor for Lynx Otter O"),
            ("MACH3", "Mach3", "Post processor for Mach3"),
            ("SHOPBOT_MTC", "ShopBot MTC", "Post processor for ShopBot MTC"),
            ("SIEGKX1", "Sieg KX1", "Post processor for Sieg KX1"),
            ("WIN_PC", "WinPC-NC", "Post processor for CNC by Burkhard Lewetz"),
        ],
        update=update_post_processor,
    )
    post_processor: bpy.props.PointerProperty(type=postprocessor.Base)
