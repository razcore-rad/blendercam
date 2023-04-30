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
from ..utils import ADDON_PATH, slugify, to_dict, from_dict, update_cam_tools_library


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
    result = self.get("type", 0)
    enum, *_ = cam_tools_library_type_items.items[result]
    if not self.tools:
        self.tools.add()
        self.save(slugify(enum))
    return result


def set_cam_tools_library_type(self, value: int) -> None:
    self["type"] = value
    enum, *_ = cam_tools_library_type_items.items[self["type"]]
    self.load(slugify(enum))


class CAMTool(PropertyGroup):
    name: StringProperty(default="Tool", update=update_cam_tools_library)

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
            ("LASER", "Laser", ""),
            ("PLASMA", "Plasma", ""),
        ],
        update=update_cam_tools_library
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
        return slugify(self.type)

    def add_library(self, context: Context, name: str) -> None:
        library = slugify(name)
        (TOOLS_LIBRARY_PATH / f"{library}.json").touch()
        self.tools.clear()
        self.tools.add()
        self.tool_active_index = 0
        self.type = library.upper()
        self.save(library)

    def remove_library(self) -> None:
        (TOOLS_LIBRARY_PATH / f"{self.library}.json").unlink(missing_ok=True)
        self.type, *_ = DEFAULT_CAM_TOOLS_LIBRARY_ITEM

    def save(self, library: str = "") -> None:
        if library == "":
            library = self.library

        with open(TOOLS_LIBRARY_PATH / f"{library}.json", "w") as f:
            py = to_dict(self)
            del py["type"]
            json.dump(py, f)

    def load(self, library: str = "") -> None:
        if library == "":
            library = self.library

        try:
            with open(TOOLS_LIBRARY_PATH / f"{library}.json", "r") as f:
                from_dict(json.load(f), self)
        except json.decoder.JSONDecodeError:
            pass

