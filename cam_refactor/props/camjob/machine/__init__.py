import importlib

import bpy

modnames = ["feedrate", "postprocessor", "spindlerpm"]

globals().update(
    {modname: importlib.reload(importlib.import_module(f".{modname}", __package__)) for modname in modnames}
)


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
    )
    anilam_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    centroid_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    fadal_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    gravos_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    grbl_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    iso_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    hafco_hm_50_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    heidenhain_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    heidenhain_530_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    heidenhain_tnc151_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    linux_cnc_post_processor: bpy.props.PointerProperty(type=postprocessor.LinuxCNCPostProcessor)
    lynx_otter_o_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    mach3_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    shopbot_mtc_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    siegkx1_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)
    win_pc_post_processor: bpy.props.PointerProperty(type=postprocessor.PostProcessor)

    @property
    def post_processor_proname(self) -> str:
        return f"{self.post_processor_enum.lower()}_post_processor"

    @property
    def post_processor(self) -> bpy.types.PropertyGroup:
        return getattr(self, self.post_processor_proname, None)
