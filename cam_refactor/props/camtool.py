import json

from bpy.props import (
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
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
from ..utils import ADDON_PATH, slugify, to_dict


TOOLS_LIBRARY_PATH = ADDON_PATH / "tools_library"
DEFAULT_CAM_TOOLS_LIBRARY_ITEM = ("DEFAULT", "Default", "")


def cam_tools_library_type_items(self, context: Context) -> None:
    TOOLS_LIBRARY_PATH.mkdir(exist_ok=True)
    items = sorted(
        ((slug := slugify(p.stem)).upper(), slug.capitalize(), "")
        for p in TOOLS_LIBRARY_PATH.glob("*.json")
    )
    if DEFAULT_CAM_TOOLS_LIBRARY_ITEM in items:
        items.remove(DEFAULT_CAM_TOOLS_LIBRARY_ITEM)
    cam_tools_library_type_items.items = [
        it + (i,) for i, it in enumerate([DEFAULT_CAM_TOOLS_LIBRARY_ITEM] + items)
    ]
    return cam_tools_library_type_items.items


cam_tools_library_type_items.items = []


def get_cam_tools_library_type(self) -> int:
    default_enum, *_ = DEFAULT_CAM_TOOLS_LIBRARY_ITEM
    result = self.get("type", 0)
    if not self.tools:
        self.tools.add()
        default_slug = f"{slugify(default_enum)}.json"
        with open(TOOLS_LIBRARY_PATH / default_slug, "w") as f:
            json.dump([{self.tool.name: to_dict(self.tool.cutter)}], f)
    return result


def set_cam_tools_library_type(self, value: int) -> None:
    self["type"] = value


class CAMTool(PropertyGroup):
    name: StringProperty(default="Tool")
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

    @property
    def library(self) -> str:
        return f"{slugify(self.type)}.json"

    def add_library(self, context: Context, name: str) -> None:
        library = slugify(name)
        (TOOLS_LIBRARY_PATH / f"{library}.json").touch()
        self.type = library.upper()

    def remove_library(self) -> None:
        (TOOLS_LIBRARY_PATH / self.library).unlink(missing_ok=True)
        self.type = "DEFAULT"
