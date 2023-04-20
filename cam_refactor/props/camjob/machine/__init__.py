from bpy.props import EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Context, PropertyGroup

from . import feedrate, postprocessor, spindlerpm
from ... import utils


def update_post_processor(machine: PropertyGroup, context: Context) -> None:
    utils.copy(context, machine.previous_post_processor, machine.post_processor)
    machine.previous_post_processor_enum = machine.post_processor_enum


class Machine(PropertyGroup):
    EXCLUDE_PROPNAMES = {"name", "post_processor_enum", "previous_post_processor_enum"}

    feed_rate: PointerProperty(type=feedrate.FeedRate)
    spindle_rpm: PointerProperty(type=spindlerpm.SpindleRPM)
    axes: IntProperty(name="Axes", default=3, min=3, max=5)
    previous_post_processor_enum: StringProperty(default="GRBL")
    post_processor_enum: EnumProperty(
        name="Post Processor",
        default="GRBL",
        items=[
            # ("ANILAM", "Anilam Crusader M", "Post processor for Anilam Crusader M"),
            # ("CENTROID", "Centroid M40", "Post processor for Centroid M40"),
            # ("FADAL", "Fadal", "Post processor for Fadal VMC"),
            # ("GRAVOS", "Gravos", "Post processor for Gravos"),
            (
                "GRBL",
                "grbl",
                "Post processor for grbl firmware on Arduino with CNC shield",
            ),
            ("ISO", "Iso", "Standardized G-code ISO 6983 (RS-274)"),
            # ("HAFCO_HM_50", "Hafco HM-50", "Post processor for Hafco HM-50"),
            # ("HEIDENHAIN", "Heidenhain", "Post processor for Heidenhain"),
            # ("HEIDENHAIN_530", "Heidenhain 530", "Post processor for Heidenhain 530"),
            # ("HEIDENHAIN_TNC151", "Heidenhain TNC151", "Post processor for Heidenhain TNC151"),
            (
                "LINUX_CNC",
                "LinuxCNC",
                "Post processor for Linux based CNC control software",
            ),
            # ("LYNX_OTTER_O", "Lynx Otter O", "Post processor for Lynx Otter O"),
            ("MACH3", "Mach3", "Post processor for Mach3"),
            # ("SHOPBOT_MTC", "ShopBot MTC", "Post processor for ShopBot MTC"),
            # ("SIEGKX1", "Sieg KX1", "Post processor for Sieg KX1"),
            # ("WIN_PC", "WinPC-NC", "Post processor for CNC by Burkhard Lewetz"),
        ],
        update=update_post_processor,
    )
    grbl_post_processor: PointerProperty(type=postprocessor.Base)
    iso_post_processor: PointerProperty(type=postprocessor.Base)
    linux_cnc_post_processor: PointerProperty(type=postprocessor.LinuxCNC)
    mach3_post_processor: PointerProperty(type=postprocessor.Base)

    @property
    def previous_post_processor(self) -> PropertyGroup:
        return getattr(
            self, f"{self.previous_post_processor_enum.lower()}_post_processor"
        )

    @property
    def post_processor_propname(self) -> str:
        return f"{self.post_processor_enum.lower()}_post_processor"

    @property
    def post_processor(self) -> PropertyGroup:
        return getattr(self, self.post_processor_propname)
