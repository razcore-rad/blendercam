from bpy.props import CollectionProperty, EnumProperty, IntProperty, PointerProperty
from bpy.types import Context, PropertyGroup

from .camjob.operation.cutter import (
    BallCutter,
    BullCutter,
    BallConeCutter,
    BullConeCutter,
    ConeCutter,
    ConeConeCutter,
    CylinderCutter,
    CylinderConeCutter,
    SimpleCutter,
)
from ..types import MediumEnumItems
from ..utils import ADDON_PATH


TOOLS_LIBRARY_PATH = ADDON_PATH / "tools_library"
DEFAULT_CAM_TOOLS_LIBRARY_ITEM = ("DEFAULT", "Default", "")


def cam_tools_library_type_items(self, context: Context) -> MediumEnumItems:
    TOOLS_LIBRARY_PATH.mkdir(exist_ok=True)
    items = sorted(
        (p.stem.upper(), p.stem.capitalize(), "")
        for p in TOOLS_LIBRARY_PATH.glob("*.json")
    )
    if DEFAULT_CAM_TOOLS_LIBRARY_ITEM in items:
        items.remove(DEFAULT_CAM_TOOLS_LIBRARY_ITEM)
    return [it + (i,) for i, it in enumerate([DEFAULT_CAM_TOOLS_LIBRARY_ITEM] + items)]


def get_cam_tools_library_type(self) -> int:
    enum, *_ = DEFAULT_CAM_TOOLS_LIBRARY_ITEM
    result = self.get("type", 0)
    if not self.tools:
        self.tools.add()
        tool = self.tools[-1]
        tool.name = tool.type.capitalize()
    return result


def set_cam_tools_library_type(self, value: int) -> None:
    self["type"] = value


class CAMTool(PropertyGroup):
    type: EnumProperty(
        items=[
            ("CYLINDER", "Cylinder", ""),
            ("BALL", "Ball", ""),
            ("BULL", "Bull", ""),
            ("CONE", "Cone", ""),
            ("CYLINDER_CONE", "Cylinder Cone", ""),
            ("BALL_CONE", "Ball Cone", ""),
            ("BULL_CONE", "Bull Cone", ""),
            ("CONE_CONE", "Cone Cone", ""),
            ("LASER_CONE", "Laser", ""),
            ("PLASMA_CONE", "Plasma", ""),
        ]
    )
    cylinder_cutter: PointerProperty(type=CylinderCutter)
    ball_cutter: PointerProperty(type=BallCutter)
    bull_cutter: PointerProperty(type=BullCutter)
    cone_cutter: PointerProperty(type=ConeCutter)
    cylinder_cone_cutter: PointerProperty(type=CylinderConeCutter)
    ball_cone_cutter: PointerProperty(type=BallConeCutter)
    bull_cone_cutter: PointerProperty(type=BullConeCutter)
    cone_cone_cutter: PointerProperty(type=ConeConeCutter)
    laser_cutter: PointerProperty(type=SimpleCutter)
    plasma_cutter: PointerProperty(type=SimpleCutter)

    @property
    def cutter(self) -> PropertyGroup:
        return getattr(self, f"{self.type.lower()}_cutter")


class CAMToolsLibrary(PropertyGroup):
    type: EnumProperty(
        name="Library",
        items=cam_tools_library_type_items,
        get=get_cam_tools_library_type,
        set=set_cam_tools_library_type,
    )
    tools: CollectionProperty(type=CAMTool)
    tool_active_index: IntProperty(default=0, min=0)

    @property
    def tool(self) -> CAMTool:
        return self.tools[self.tool_active_index]
