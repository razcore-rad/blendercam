from itertools import tee
from typing import Iterator

from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Context, PropertyGroup
from mathutils import Vector

from . import feedmovementspindle, strategy, workarea
from ....types import ComputeResult
from ....utils import copy


def update_operation_strategy(self, context: Context) -> None:
    copy(context, self.previous_strategy, self.strategy)
    self.previous_strategy_type = self.strategy_type


def search_operation_tool(self, context: Context, edit_text: str) -> Iterator[str]:
    tools = context.scene.cam_tools_library.tools
    return (f"{i + 1}: {t.name}" for i, t in enumerate(tools))


def update_operation_tool(self, context: Context) -> None:
    self.tool_id = -1
    try:
        self.tool_id = int(self.tool.split(":")[0]) - 1
    except ValueError:
        pass


class Operation(PropertyGroup):
    EXCLUDE_PROPNAMES = {
        "previous_strategy_type",
        "tool_id",
        "tool",
    }
    NAME = "CAMOperation"

    is_hidden: BoolProperty(default=False)
    previous_strategy_type: StringProperty(default="PROFILE")
    strategy_type_items = [
        ("BLOCK", "Block", "Block path"),
        (
            "CARVE_PROJECT",
            "Carve Project",
            "Project a curve object on a 3D surface",
        ),
        ("CIRCLES", "Circles", "Circles path"),
        ("CROSS", "Cross", "Cross paths"),
        ("CURVE_TO_PATH", "Curve to Path", "Convert a curve object to G-code path"),
        ("DRILL", "Drill", "Drill"),
        (
            "MEDIAL_AXIS",
            "Medial axis",
            (
                "Medial axis, must be used with V or ball cutter, for engraving"
                " various width shapes with a single stroke"
            ),
        ),
        (
            "OUTLINE_FILL",
            "Outline Fill",
            (
                "Detect outline and fill it with paths as pocket then sample"
                " these paths on the 3D surface"
            ),
        ),
        ("PARALLEL", "Parallel", "Parallel lines at any angle"),
        ("POCKET", "Pocket", "Pocket"),
        ("PROFILE", "Profile", "Profile cutout"),
        ("SPIRAL", "Spiral", "Spiral path"),
        (
            "WATERLINE_ROUGHING",
            "Waterline Roughing",
            "Roughing below ZERO. Z is always below ZERO",
        ),
    ]
    strategy_type: EnumProperty(
        name="Strategy",
        items=strategy_type_items,
        default="PROFILE",
        update=update_operation_strategy,
    )
    block_strategy: PointerProperty(type=strategy.Block)
    circles_strategy: PointerProperty(type=strategy.Circles)
    cross_strategy: PointerProperty(type=strategy.Cross)
    carve_project_strategy: PointerProperty(type=strategy.CarveProject)
    curve_to_path_strategy: PointerProperty(type=strategy.CurveToPath)
    drill_strategy: PointerProperty(type=strategy.Drill)
    medial_axis_strategy: PointerProperty(type=strategy.MedialAxis)
    outline_fill_strategy: PointerProperty(type=strategy.OutlineFill)
    parallel_strategy: PointerProperty(type=strategy.Parallel)
    pocket_strategy: PointerProperty(type=strategy.Pocket)
    profile_strategy: PointerProperty(type=strategy.Profile)
    spiral_strategy: PointerProperty(type=strategy.Spiral)
    waterline_roughing_strategy: PointerProperty(type=strategy.WaterlineRoughing)

    tool_id: IntProperty(default=-1)
    tool: StringProperty(
        name="Tool", search=search_operation_tool, update=update_operation_tool
    )

    feed: PointerProperty(type=feedmovementspindle.Feed)
    movement: PointerProperty(type=feedmovementspindle.Movement)
    spindle: PointerProperty(type=feedmovementspindle.Spindle)
    work_area: PointerProperty(type=workarea.WorkArea)

    @property
    def zero(self) -> dict:
        return {
            "vector": (0.0, 0.0, self.movement.rapid_height),
            "rapid_height": self.movement.rapid_height,
            "feed_rate": self.feed.rate,
            "plunge_scale": self.feed.plunge_scale,
            "spindle_direction": self.spindle.direction_type,
            "spindle_rpm": self.spindle.rpm,
            "dwell": 0.0,
        }

    @property
    def previous_strategy(self) -> PropertyGroup:
        return getattr(self, f"{self.previous_strategy_type.lower()}_strategy")

    @property
    def strategy(self) -> PropertyGroup:
        return getattr(self, f"{self.strategy_type.lower()}_strategy")

    def get_cutter(self, context: Context) -> PropertyGroup:
        return context.scene.cam_tools_library.tools[self.tool_id].cutter

    def get_bound_box(self, context: Context) -> tuple[Vector, Vector]:
        result = Vector(), Vector()
        try:
            vectors = (
                o.matrix_world @ Vector(c)
                for o in self.strategy.get_source(context)
                for c in o.bound_box
            )
            result = tuple(
                Vector(f(cs) for cs in zip(*ps))
                for f, ps in zip((min, max), tee(vectors))
            )
        except ValueError:
            pass
        return result

    def get_depth_end(self, context: Context) -> float:
        result = 0
        if self.work_area.depth_end_type == "CUSTOM":
            result = self.work_area.depth_end
        if self.work_area.depth_end_type == "SOURCE":
            bound_box_min, _ = self.get_bound_box(context)
            result = bound_box_min.z
        elif self.work_area.depth_end_type == "STOCK":
            stock_bound_box_min, _ = context.scene.cam_job.get_stock_bound_box(context)
            result = stock_bound_box_min.z
        return result

    def execute_compute(self, context: Context, last_position: Vector) -> ComputeResult:
        return self.strategy.execute_compute(context, self, last_position)

    def add_data(self, context: Context) -> None:
        self.name = self.NAME
        if self.strategy.object_source is None:
            self.strategy.object_source = context.object
        if self.strategy.collection_source is None:
            self.strategy.collection_source = context.collection

        cam_tools_library = context.scene.cam_tools_library
        self.tool_id = cam_tools_library.tools.values().index(cam_tools_library.tool)
        self.tool = f"{self.tool_id + 1}: {cam_tools_library.tool.name}"
